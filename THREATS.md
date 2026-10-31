# Threats

What a contribution to an open NoWayOS repository might try, on purpose or by
mistake. Each threat has an ID that [GATES.md](GATES.md) cites; the last column
names the gates that answer it.

NoWayOS is a secure station: what it builds runs where people type things that
matter. So we assume a pull request may come from someone persistent, capable and
hostile, or from a tool that writes plausible code nobody has checked. Neither
is judged by who sent it.

| ID | Threat | What it looks like | Answered by |
| --- | --- | --- | --- |
| TH1 | **Code run at build or test time** | A `build.rs`, a procedural macro, a test, a Makefile, a make fragment or a tool in the pull request runs on the reviewer's machine or CI host. It can read whatever the build can see, send it out, or change what is built | P4, P3; stage 4 runs only after the patch checks, offline, on read-only mounts, with no secrets |
| TH2 | **Weakening a gate in the same change** | An allowlist, baseline or `deny.toml` exception widened; an `.expect` file's forbidden line dropped or a `.grants` file given more; a test deleted, `#[ignore]`d or its assertion loosened; an `#[allow]` added; a proof or mutant dropped; a step taken out of `make ci` | P2, P7, P8, Q6, B3, B5, B9, B13, B15, B17, B22 |
| TH3 | **Dependencies** | A new crate or git dependency; a name one letter from a well-known crate; a crate whose owner has changed; a feature that pulls in `std` or `unsafe`; a licence that is not permissive | P3, Q8, B4, B6, B7, B8, B9, B10, B20 |
| TH4 | **Trojan source** | Bidirectional controls and invisible characters that make code read differently from how it compiles; identifiers that look like others; binary files; generated files that do not match their source | P5, P6, Q5, B14 |
| TH5 | **A long con** | Trust built over many small, good pull requests, then a subtle one: an off-by-one in a bounds check, a check moved after the use, a value logged that should not be | Every gate judges the change alone, never its author's record ([GATES.md](GATES.md#verdicts)); T2, Q2, Q3, Q4, Q5, B2, B3, B11, B12, B13, B17, B18 |
| TH6 | **Prompt injection against the reviewer** | Text anywhere in a pull request - code, comments, strings, file names, commit messages, its title and body, fixtures - that addresses the reviewer, asks for a verdict or says a check does not apply | Q1; Claude follows only Defence Agent's instructions (README, principle 2) |
| TH7 | **Volume** | Many plausible but wrong pull requests, often written by AI, more than maintainers can read | T1, T2, Q2 |
| TH8 | **Laundered code** | Code copied from a GPL or other copyleft project, or from a vendor's source under terms we cannot meet, presented as new | P1, T3, Q7 |
| TH9 | **Secrets and private material** | A key, token or credential; a client's or customer's name; private notes | P11, B1 |
| TH10 | **CI and pins** | A workflow file changed; `nowayos.rev`, a toolchain, the dev image's pins or a lock file moved to something unexpected | P2, P9, P10, B7, B16, B19, B21 |

## What is out of scope here

- Attacks on a running NoWayOS device. Those are the product's own threat model;
  the gates here check that a change keeps the product's controls (B9, B15, B17).
- A maintainer acting in bad faith. The rules in [OWNERS.md](OWNERS.md) - a
  gate changes only with the Product Owner's approval - are the answer to that,
  not a tool.
