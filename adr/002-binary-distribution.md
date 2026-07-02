# ADR-002 — Binary distribution for end-user install

- **Status:** Accepted
- **Date:** 2026-07-03
- **Deciders:** maintainers

## Context

`drive-uploader` is a Python service that watches a local folder and
uploads new files to Google Drive. The current install path is
developer-oriented: clone the repo, install `uv`, run `uv sync`, then
launch the service from a terminal with `make run`. This is a non-starter
for the target audience: Windows or Linux workstation users who are not
Python developers and do not have `uv`, Python 3.11, or git on their
machines.

We need an end-user install path that produces a runnable service from
a single download on each target OS, with a sensible first-run
experience and a stable per-user location for settings and state.

Constraints that shaped the decision:

- The audience is workstations, not servers; they run the service by
  hand in a logged-in session and stop it with Ctrl+C.
- Cross-platform: Windows 10/11 and a current Linux distribution.
- The codebase is hexagonal (see ADR-001); packaging must not push
  infrastructure concerns into `domain/` or `application/`.
- Project conventions: PEP 420 implicit-namespace `src/` layout, no
  `__init__.py` files, `src.`-prefixed imports, no new runtime
  dependencies (stdlib + uv-managed Google libs + watchdog only).
- Build and release engineering capacity is small — no dedicated
  release engineer, so the path must be sustainable from CI without
  local babysitting per OS.

## Decision

Distribute `drive-uploader` as a **PyInstaller onefile console-mode
binary** per OS, published to **GitHub Releases** via a CI workflow
that runs on every `v*` tag push.

Key shape:

- The binary bundles the application code, third-party dependencies
  (`google-api-python-client`, `google-auth`, `google-auth-oauthlib`,
  `watchdog`), and a `.env.example` template. Stdlib is bundled via
  PyInstaller's PYZ archive. PEP 420 implicit-namespace packages
  (`src.*`) are bundled as data and made importable via a tiny
  runtime hook that prepends the extracted `src/` to `sys.path`.
- The build is driven by a checked-in `drive-uploader.spec` (PyInstaller
  spec file) at repo root and a `make build` target that runs
  PyInstaller locally for dev smoke testing.
- A GitHub Actions workflow (`.github/workflows/release.yml`) builds
  the binary on both `ubuntu-latest` and `windows-latest`, computes
  SHA256 checksums, and attaches the artefacts (renamed to
  `drive-uploader-vX.Y.Z-{linux-amd64,windows-amd64.exe}` plus
  `SHA256SUMS`) to the GitHub Release created from the tag.
- On first run with an empty per-user config directory the binary
  runs an interactive wizard that prompts for the three required
  settings, validates them (path-exists checks), and writes a `.env`
  file. Subsequent runs skip the wizard.
- Per-user config lives at the platform-standard location:
  `%APPDATA%\DriveUploader\` on Windows and
  `$XDG_CONFIG_HOME/drive-uploader/` (with `~/.config/drive-uploader/`
  fallback) on Linux. SQLite queue and OAuth token files live alongside
  `.env` in the same directory.
- The wizard refuses to run on non-TTY stdin and the entry point prints
  a friendly error explaining how to create `.env` manually.
- A best-effort `check_for_new_version()` consults the GitHub Releases
  API on startup and prints a one-liner if a newer tag exists; failure
  is silent and never blocks startup.
- The service runs in the foreground and logs to the console. There
  is no GUI, no system tray, no auto-start on login, no service
  registration.

## Alternatives considered

- **OS packages (`.msi` via WiX/Inno Setup on Windows, `.deb` via
  `fpm` on Linux).** Pros: native install/uninstall experience,
  registration in "Add/Remove Programs", standard paths, can wire up
  autostart via OS mechanisms. Cons: significantly more build tooling
  (WiX toolset, Inno Setup, fpm), per-OS packaging knowledge required,
  needs code-signing certs for Windows to avoid SmartScreen warnings
  entirely, slower CI runs. Rejected for v1: the additional tooling
  and signing cost outweigh the polish gain when the audience is
  small and the deployment is manual.
- **Source-only install (current).** Pros: zero build pipeline,
  works today. Cons: requires Python 3.11 + `uv` + git on every
  workstation; non-developers cannot install it. Rejected as the
  primary path; preserved as `make install` / `make run` for
  developers.
- **Container-based distribution (Docker).** Pros: hermetic, OS-portable.
  Cons: requires Docker Desktop on Windows (extra install, often
  blocked by corporate IT), doesn't fit the "foreground workstation
  tool" model cleanly (containers run as background services by
  default), state management under named volumes is more obscure than
  a simple per-user config dir. Rejected: the audience is not
  server operators; container overhead is wasted on a single-user
  foreground tool.
- **Python package on PyPI + `pipx run drive-uploader`.** Pros: no
  build step. Cons: still requires Python on the target, and `pipx`
  is itself an install step; doesn't satisfy the "no Python on the
  target machine" requirement.

## Consequences

Positive:

- End users can install by downloading one file per OS, verifying
  one checksum, and double-clicking (or `chmod +x && ./...`). No
  Python, `uv`, or git on the target.
- Cross-OS builds run automatically on tag push; no manual
  cross-compilation or multi-OS dev environment.
- Project conventions survive the packaging work: `domain/` and
  `application/` are unchanged; the only `infrastructure/` change is
  a thin wizard module in `bootstrap/`; `import-linter` contracts
  (`core-knows-no-adapters`, `adapters-dont-reach-into-each-other`)
  remain green.
- New runtime dependencies introduced: zero. The `.env` parser and
  config-dir resolver are stdlib only. The version check uses
  `urllib.request` from stdlib.

Accepted negatives (deferred from v1):

- **No code signing.** Windows SmartScreen will warn on first launch.
  The README documents the "More info → Run anyway" workaround.
  Acquire a code-signing certificate and wire it into the CI
  workflow when the friction becomes unacceptable.
- **No package-manager distribution.** Users will not find
  `drive-uploader` via `winget`, `scoop`, or `apt`. Adding the
  manifests and submitting them is mechanical but requires external
  review (Microsoft, scoop-extras maintainers, Debian NEW queue).
- **No auto-update mechanism** beyond the best-effort one-liner on
  startup. Users upgrade by re-downloading.
- **No service / daemon registration.** No `systemd` unit, no Windows
  Service SCM entry, no auto-start on login. Users start and stop the
  service manually.
- **No GUI / tray icon.** The binary is a foreground terminal process.
- **PEP 420 namespace workaround.** PyInstaller's static analysis
  cannot follow implicit-namespace `src.*` imports; the spec bundles
  `src/` as data and a runtime hook prepends the extracted path so
  Python's namespace-package machinery finds submodules. This is
  fragile if the implicit-namespace layout ever changes; documented
  here so a future maintainer does not accidentally break it by
  adding `__init__.py` files.

Open questions / future work:

- The Service-Account vs OAuth-InstalledAppFlow drift in the auth
  layer (tracked under ADR-001 M3) is unrelated to this decision and
  out of scope here. When that drift is resolved, this ADR's
  `.env.example` and wizard prompts may need to be updated.
- Code-signing cert acquisition is the next obvious investment once
  SmartScreen friction starts costing more than the cert.
- Migrating to `onedir` mode in PyInstaller would reduce startup
  latency at the cost of shipping a directory; deferred until measured.