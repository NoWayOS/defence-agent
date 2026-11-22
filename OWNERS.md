# Owners

Who may change a gate, and which files in each open repository belong to the
gates rather than to the code they judge.

## Who may change a gate

- **The Product Owner decides** every change to a gate: this repository, a
  gate-owned path below, or a tool a gate runs. The Product Owner is the open
  repositories' maintainer and copyright holder; reach them through an issue
  or a pull request here, and with a vulnerability, privately, as SECURITY.md
  says.
- **Anyone may propose one**, by a pull request or an issue. A pull request that
  touches a gate-owned path stops at P2 until the Product Owner has read it.
- **No change judges itself.** A pull request that changes a gate is judged by
  the gates as they were at its base commit.

A change that loosens a gate says why in its description and in the file it
changes: an allowlist entry, a `deny.toml` exception and a `secrets-allow.toml`
entry each carry their reason. A licence that is not permissive (MIT,
Apache-2.0, BSD, ISC) needs the Product Owner's written sign-off before it goes
in.

## Gate-owned paths

A pull request to the repository that touches one of these goes to the Product
Owner (P2). `**` means anything below; `*` anything in one folder or name.

### Every repository

- `Makefile`
- `.github/**` and any other CI configuration
- `.gitattributes`: it can hide a file's changes from a reviewer
- `**/.cargo/**`: it can change how the code is built and run
- `rust-toolchain.toml`, `**/rust-toolchain.toml`
- `deny.toml`, `**/deny.toml`
- `secrets-allow.toml`
- `Cargo.toml`, `Cargo.lock`: the root workspace's; a repository's other workspaces are listed in its
  own section

### NoWayOS (`nowayos`)

- `tools/**`: every tool, the make fragments (`tools/make/`), the dev image
  (`tools/container/`) and the policy files - `baseline.toml`,
  `unsafe-allowlist.toml`, `grant-rules.toml`, `sel4-verification.toml`,
  `image-components.toml`, `initialiser-audit.toml`, `crypto-crates.txt`
- `pds/Cargo.toml`, `pds/Cargo.lock`, `fuzz/Cargo.toml`, `fuzz/Cargo.lock`: the PD and fuzz
  workspaces' manifests and locks
- `pds/std-crates.txt`
- `systems/**`: system descriptions and their `.grants`, `.expect`, `.qmp`
  files and approved screens
- `crates/*/src/proofs.rs`, `fuzz/fuzz_targets/**`

### Screen Compiler (`screen-compiler`)

- `contract-check/**`: the check that every generated screen builds against
  NoWayOS and draws as approved, with its approved images (`contract-check/golden/`)
- `tools/**`: the screens tool, which the starter's check that its screens convert as checked in runs

### Showcase (`showcase`)

- `nowayos.rev`
- `pds/Cargo.toml`, `pds/Cargo.lock`, `fuzz/Cargo.toml`, `fuzz/Cargo.lock`: the PD and fuzz
  workspaces' manifests and locks
- `tools/**`: `check-nowayos-rev`, `check-quiet`, `kani-mutations.json` and the
  screens tool
- `systems/**`: system descriptions and their `.grants`, `.expect` and `.qmp`
  files
- `**/src/proofs.rs`, `fuzz/fuzz_targets/**`

### Starter (`starter`)

- `setup`: it decides what `make setup` fetches, and from where
- `nowayos.rev`, `screen-compiler.rev`
- `app/Makefile`
- `app/Cargo.toml`, `app/Cargo.lock`, `app/pds/Cargo.toml`, `app/pds/Cargo.lock`
- `app/tools/**`: `check-pins`, `new-screen` and `rename`
- `app/systems/**`: the system description and its `.grants`, `.expect` and
  `.qmp` files and approved screen
- `.vscode/**`: an editor can run what a task file names

### Defence Agent (`defence-agent`)

- Everything.

## Binary files a pull request may carry

P6 fails any other binary file. These go to a maintainer, who looks at each.

- NoWayOS: approved images in `crates/nowayos-demo/session/`,
  `crates/nowayos-render-eg/tests/snapshots/` and `systems/`; the pictures the
  picture decoder is tested with, in
  `crates/nowayos-picture-decode/tests/pictures/`, and the example pictures in
  `crates/nowayos-pictures/pictures/`; the README's picture in `assets/`; the
  pinned font in `crates/nowayos-glyphs/fonts/`; the generated atlases and icon
  masks in `crates/nowayos-glyphs/src/atlas/` and
  `crates/nowayos-icons/src/masks/`, which B14 makes again and compares.
- Screen Compiler: approved images in `contract-check/golden/`.
- Showcase: approved images in `systems/` and
  `showcase/showcase-app/tests/snapshots/`; the README's picture in `assets/`.
- Starter: the approved screen in `app/systems/`.

## Policy files

The policy files a gate reads - allowlists, baselines, `deny.toml`, grant rules,
expect files - live today in the repository each one guards, at the paths
above. Defence Agent will keep the master copy of each and judge with it; a
repository's copy, kept for local runs, that differs from the master will fail
a gate.
