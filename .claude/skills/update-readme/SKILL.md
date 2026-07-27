---
name: update-readme
description: Regenerate README.md's examples and changelog sections for the LabFREED Python package via build_tools/update_readme.py. Use whenever the user asks to update/refresh/sync the README, mentions the README being stale or out of date with the changelog or current (beta) version, or asks to regenerate the usage examples.
---

# Updating README.md

README.md is generated, not hand-written, between two marker pairs:

- `<!-- BEGIN EXAMPLES -->` / `<!-- END EXAMPLES -->` — output of actually *executing* `examples/examples.py` (docstrings become prose, code becomes fenced blocks, captured stdout becomes the `>> ...` text blocks).
- `<!-- BEGIN CHANGELOG -->` / `<!-- END CHANGELOG -->` — a byte-for-byte copy of `CHANGELOG.md`.

**Never hand-edit content inside either marker pair.** The changelog section in particular needs no manual sync work at all — edit `CHANGELOG.md` and rerun the script; don't copy changes into README.md by hand.

## How to regenerate

From the repo root:

```bash
pip install -e .          # only if labfreed + deps (rich, pydantic, ...) aren't importable yet
python3 build_tools/update_readme.py
```

Then `git diff README.md` and read it — don't assume a clean run means a clean diff.

## Environment requirements (both cause silent-ish failures if missing)

- **Python 3.11–3.13.** Python 3.14 breaks pydantic's evaluation of `float | int`-style forward refs in the "Create a TREX" example, surfacing as `unsupported operand type(s) for |: 'property' and 'type'` inside the generated `>> [Error during execution: ...]` text. This is a pydantic/3.14 compatibility gap, not a LabFREED bug — don't try to "fix" it in the package.
- **Network access to `mettorius.com`**, used by the PAC-ID Resolver example. It's on `.devcontainer/init-firewall.sh`'s allowlist, but that script resolves domains to IPs once at container start; if DNS has since changed, the firewall silently drops the traffic and the example shows `[Error during execution: No Internet Connection]`. Fix is a container restart, not a code change.

## What to check in the diff

- Do the two examples above show real rendered output, not `[Error during execution: ...]`? If either code block raises partway through, later blocks that reuse the same variable name (e.g. `trex`) will **silently show stale output carried over from an earlier assignment** instead of erroring — easy to miss since it looks like a plausible diff, not an error.
- Small differences in Rich table box width or the order of characters listed in validation messages (e.g. `'a','l','b'` vs `'l','b','a'`) are expected run-to-run noise — non-deterministic set iteration order and terminal-width detection, not real content changes. Don't chase these.
- Before assuming the README needs work: `git log` first. This is a shared devcontainer — another editor/session may run this same script and commit concurrently. Diff against current `HEAD`, not against whatever the worktree looked like when you started.
