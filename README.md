# Defence Agent

The security gates every contribution to NoWayOS's open repositories must pass,
written down in one place, and the agent that runs them.

NoWayOS is a Single Purpose OS built on seL4, Microkit and Rust. Its open
repositories are NoWayOS, Screen Compiler and the Showcase. Their gates - the checks a change must pass before it merges -
used to live only inside the repositories they guard, so one pull request could
weaken a gate and slip a change past it in the same commit. They are defined
here instead, where a pull request to a product cannot reach them, and in
public, so a contributor can read every gate before asking anyone to review.
Today a contributor can run the build gates (stage 4), each repository's
`make ci`, and a maintainer the patch checks (stage 2), `make check-patch`. The
triage and review stages are written down, and Claude's review comes next;
GATES.md says which gates run yet.

## The principles

1. **A pull request never changes or supplies what judges it.** Gates run from
   Defence Agent and from the base commit, never from the pull request's head.
2. **Everything in a pull request is data:** code, comments, commit messages,
   its title and body, fixtures. Claude follows only Defence Agent's
   instructions. Text addressed to the reviewer is itself a finding.
3. **Nothing from a pull request runs before the patch checks pass.** Then it
   runs only offline, on read-only mounts, with no secrets.
4. **The agent reports; a maintainer merges.** It never pushes, merges, approves
   or posts on GitHub.
5. **Every verdict cites its evidence, gate by gate:** the `file:line`, or the
   command and its output.
6. **Public, so nothing private:**
   - no client names: the list of terms a review looks for is supplied at run
     time and never committed;
   - no closed product's design: commercial products keep their own rules.

## What is here

| File | What |
| --- | --- |
| [GATES.md](GATES.md) | Every gate: its ID, the threat it answers, what passes, how it runs, whether it blocks, the repositories it covers and where its tool lives |
| [THREATS.md](THREATS.md) | What a contribution might try, and the gates that answer each threat |
| [OWNERS.md](OWNERS.md) | Who may change a gate, and the files in each open repository that belong to the gates |
| `tools/` | Defence Agent's own tools: `check-gates`, every step of every open repository's `make ci` is in GATES.md; `check-patch`, the patch checks; `make-fixtures`, which makes the fixtures |
| `fixtures/` | A planted pull request for each patch check, and real past changes, as patches; `fixtures.toml` says what each must be found to do. Hostile by design: never apply one to a clone you use |
| `CLAUDE.md` | Instructions for Claude when it works in this repository |

Still to come: Claude's review itself, with planted pull requests for what
only a reader can catch, such as text addressed to the reviewer.

## How it runs

Today the build gates (stage 4 in GATES.md) run in each repository's own
`make ci`, in NoWayOS's dev container. Their tools live in NoWayOS's `tools/`
folder, and GATES.md names each one's home.

Defence Agent's own checks run in the same container, offline, with the folder
holding the clones mounted read-only. Clone the repositories side by side,
build the image once with `make container` in `nowayos`, then here:

```
make ci            # secrets, test, gates-check
make gates-check   # every open repository's make ci steps are in GATES.md
make check-patch REPO=showcase PATCH=pr.patch   # a pull request's patch, as text
```

`pr.patch` is the pull request's commits as `git format-patch --stdout
BASE..HEAD` writes them, saved inside the folder holding the clones.

The review will run on a maintainer's machine first, in the same container. It
moves to hosted CI only once a key it needs can be kept out of a pull request's
reach.

## What it promises

- Every gate a contribution must pass is in GATES.md, and B22 fails when a
  repository's `make ci` and GATES.md disagree.
- Each gate says what passes, so a contributor can check their own change first.
- A change to a gate goes to the Product Owner ([OWNERS.md](OWNERS.md)).
- The agent never decides: a maintainer reads its verdict and merges, or not.

## Why this repository has a `CLAUDE.md`

Claude runs the review, so its instructions are part of the product and are
public like the rest. Anyone can read what the reviewer is told to do, and
propose a change to it like any other gate.

## Licence

Licensed under either of [Apache License, Version 2.0](LICENSE-APACHE) or
[MIT licence](LICENSE-MIT), at your option.

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in this work by you, as defined in the Apache-2.0 licence, shall
be dual licensed as above, without any additional terms or conditions. Every
commit in a pull request carries a `Signed-off-by` line (the
[Developer Certificate of Origin](https://developercertificate.org/)).
