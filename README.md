# Defence Agent

The security gates every contribution to NoWayOS's open repositories must pass,
written down in one place, and the agent that runs them.

NoWayOS is a secure station built on seL4, Microkit and Rust. Its open
repositories are NoWayOS, Screen Compiler and the Showcase. Their gates - the checks a change must pass before it merges -
used to live only inside the repositories they guard, so one pull request could
weaken a gate and slip a change past it in the same commit. They are defined
here instead, where a pull request to a product cannot reach them, and in
public, so a contributor can run the same gates before asking anyone to review.

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
| `tools/` | Defence Agent's own tools. Today, `check-gates`: every step of every open repository's `make ci` is in GATES.md |
| `CLAUDE.md` | Instructions for Claude when it works in this repository |

Still to come: the checks that read a pull request's patch without building it,
a planted pull request for each threat to prove they are caught, and Claude's
review itself.

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
```

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
[MIT licence](LICENSE-MIT), at your option. Copyright Jon Anthony.

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in this work by you, as defined in the Apache-2.0 licence, shall
be dual licensed as above, without any additional terms or conditions. Every
commit in a pull request carries a `Signed-off-by` line (the
[Developer Certificate of Origin](https://developercertificate.org/)).
