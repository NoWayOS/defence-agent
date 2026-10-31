"""Tests for tools/check-gates (gate B22)."""

import contextlib
import importlib.machinery
import importlib.util
import io
import os
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    loader = importlib.machinery.SourceFileLoader("check_gates", os.path.join(HERE, "check-gates"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


check_gates = load()

# A product's Makefile: ci-local's prerequisites over continuation lines,
# with target-specific variables and conditional branches around it.
PRODUCT = """\
LOCKED ?=
EXTRA := quiet-check
ci-local: override LOCKED := --locked
kani fuzz: CI_SCOPE := full
ci-local: secrets lint test \\
\tdeny $(EXTRA)

ifeq ($(NOWAYOS_CONTAINER),1)
ci: ci-local
secrets:
\tpython3 tools/secrets-scan # not a rule: secrets-scan: x
else
lint test ci:
\t@echo host
endif
"""

# NoWayOS's form: make ci is container-ci, in a fragment the Makefile includes,
# whose recipe runs the *_steps variables.
PLATFORM = """\
-include tools/make/system.mk
ci: container-ci
"""

FRAGMENT = """\
_root_steps := secrets lint
_system_steps := tools-test \\
\tqemu-test-all
define helper
\tnot-a-rule: secrets
endef
container-ci:
\t$(MAKE) -C . $(_root_steps) CARGO=cargo $(_scope_args)
\t$(MAKE) -f tools/make/system.mk $(_system_steps)
"""

GATES = """\
# Gates

| ID | Gate |
| --- | --- |
| B1 | Secrets |
| B2 | Lints |
| B3 | Tests |

## Every make ci step

Steps, in order.

| Repo | Step | Gates |
| --- | --- | --- |
{rows}

## After
"""


class Fixture:
    def __init__(self, root):
        self.root = root

    def write(self, path, text):
        full = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
        return full

    def gates(self, rows):
        return self.write("GATES.md", GATES.format(rows="\n".join(rows)))


class CheckGatesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)
        self.product = os.path.dirname(self.fx.write("product/Makefile", PRODUCT))
        self.platform = os.path.dirname(self.fx.write("platform/Makefile", PLATFORM))
        self.fx.write("platform/tools/make/system.mk", FRAGMENT)
        self.repos = {"product": self.product, "platform": self.platform}

    def tearDown(self):
        self.tmp.cleanup()

    def rows(self, product=("secrets", "lint", "test", "deny", "quiet-check"),
             platform=("secrets", "lint", "tools-test", "qemu-test-all")):
        return [f"| product | `{s}` | B1 |" for s in product] + [f"| platform | `{s}` | B2, B3 |" for s in platform]

    def test_reads_ci_local(self):
        self.assertEqual(check_gates.ci_steps(self.product), ["secrets", "lint", "test", "deny", "quiet-check"])

    def test_reads_container_ci_from_an_included_fragment(self):
        self.assertEqual(check_gates.ci_steps(self.platform), ["secrets", "lint", "tools-test", "qemu-test-all"])

    def test_passes_when_they_agree(self):
        problems, total = check_gates.check(self.fx.gates(self.rows()), self.repos)
        self.assertEqual(problems, [])
        self.assertEqual(total, 9)

    def test_fails_on_a_step_the_table_lacks(self):
        problems, _ = check_gates.check(self.fx.gates(self.rows(product=("secrets", "lint", "test", "deny"))), self.repos)
        self.assertEqual(len(problems), 1)
        self.assertIn("make ci runs 'quiet-check'", problems[0])

    def test_fails_on_a_step_no_make_ci_runs(self):
        rows = self.rows(platform=("secrets", "lint", "tools-test", "qemu-test-all", "kani"))
        problems, _ = check_gates.check(self.fx.gates(rows), self.repos)
        self.assertEqual(len(problems), 1)
        self.assertIn("lists 'kani', which its make ci does not run", problems[0])

    def test_fails_on_steps_out_of_order(self):
        rows = self.rows(product=("lint", "secrets", "test", "deny", "quiet-check"))
        problems, _ = check_gates.check(self.fx.gates(rows), self.repos)
        self.assertEqual(len(problems), 1)
        self.assertIn("out of order", problems[0])

    def test_fails_on_an_undefined_gate_or_none(self):
        rows = self.rows()
        rows[0] = "| product | `secrets` | B9 |"
        rows[1] = "| product | `lint` |  |"
        problems, _ = check_gates.check(self.fx.gates(rows), self.repos)
        self.assertEqual(len(problems), 2)
        self.assertIn("names gate B9", problems[0])
        self.assertIn("names no gate", problems[1])

    def test_fails_on_a_repository_not_given(self):
        rows = self.rows() + ["| elsewhere | `secrets` | B1 |"]
        problems, _ = check_gates.check(self.fx.gates(rows), self.repos)
        self.assertEqual(len(problems), 1)
        self.assertIn("'elsewhere', which was not given", problems[0])

    def test_a_makefile_with_no_readable_ci_is_an_error(self):
        self.fx.write("product/Makefile", "ci:\n\t$(IN_CONTAINER) make everything\n")
        with self.assertRaises(check_gates.InputError):
            check_gates.ci_steps(self.product)

    def test_container_ci_with_no_steps_variable_is_an_error(self):
        self.fx.write("platform/tools/make/system.mk", "container-ci:\n\t$(MAKE) everything\n")
        with self.assertRaises(check_gates.InputError):
            check_gates.ci_steps(self.platform)

    def test_an_include_outside_the_repository_is_not_read(self):
        self.fx.write("outside.mk", "ci-local: stolen\n")
        self.fx.write("platform/Makefile", "-include ../outside.mk\n" + PLATFORM)
        self.assertNotIn("stolen", check_gates.ci_steps(self.platform))

    def test_gates_without_the_steps_table_is_an_error(self):
        path = self.fx.write("GATES.md", "# Gates\n\n| ID | Gate |\n| --- | --- |\n| B1 | Secrets |\n")
        with self.assertRaises(check_gates.InputError):
            check_gates.check(path, self.repos)

    def test_main_exit_status_and_list(self):
        gates = self.fx.gates(self.rows())
        args = [f"product={self.product}", f"platform={self.platform}"]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(check_gates.main(["--gates", gates] + args), check_gates.EXIT_PASS)
            self.assertEqual(check_gates.main(["--list"] + args), check_gates.EXIT_PASS)
        self.assertIn("product quiet-check\n", out.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(check_gates.main(["--gates", gates, f"product={self.product}"]), check_gates.EXIT_FAIL)
            self.assertEqual(check_gates.main(["--gates", gates, "product"]), check_gates.EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()
