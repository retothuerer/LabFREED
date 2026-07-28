---
name: versioning
description: Semantic-versioning policy for the labfreed package -- how to classify a change as breaking or not, which version segment to bump, how to deprecate a public API before removing it, and how alpha/beta pre-releases to PyPI work. Use whenever a change under development renames/removes/restructures anything importable from `labfreed`, changes a method signature or its observable behavior, tightens validation in a way that could newly reject previously-accepted input, or when preparing a release or pre-release (bumping `labfreed/__init__.py`'s `__version__` and writing the CHANGELOG.md entry).
---

# Versioning policy

Documented for users in README.md's "Versioning" section -- this skill is the
development-side counterpart: how to actually apply that policy while working on the
code, not just what it promises.

`MAJOR.MINOR.PATCH`, per [SemVer](https://semver.org). `__version__` lives in
`labfreed/__init__.py`; `pyproject.toml` reads it from there (`dynamic = ["version"]`).

## Classifying a change

**Breaking** -- anything that could make previously-working caller code stop working or
change behavior it was relying on:
- Renaming, removing, or moving a public class/function/property/field (including
  module reorganization that changes import paths)
- Changing a method's signature (params added without a default, params removed,
  param/return type changed incompatibly)
- Renaming or removing an enum/constant a caller might reference by name
- Tightening validation so previously-accepted input is now rejected, or changing
  serialized output a caller might parse
- Changing a default value that alters existing callers' behavior

**Not breaking** -- safe to ship as minor/patch without a deprecation cycle:
- Adding a new public class/function/module
- Adding a new optional parameter with a default that preserves old behavior
- Internal refactor that doesn't change the public surface
- A bugfix restoring behavior the docs/spec always promised (fixing something clearly
  wrong isn't "breaking" the old, wrong behavior -- but see the note on validation below)

**Ambiguous, decide deliberately, don't default silently:**
- A bugfix that happens to change output for inputs that were already spec-invalid
  (e.g. the empty-`id segment` rejection documented in
  `developer-docs/design-choices.md`) -- these usually ship as **MINOR** with an
  explicit `BREAKING` tag in the changelog, per the "minor reserves the right to break
  edge cases" clause, rather than being held for a major bump. If you're not sure
  whether a case is "already spec-invalid" versus "someone could reasonably be relying
  on this," ask rather than assume.

## Picking the version bump

- **MAJOR** -- reserved for breaking changes. A major bump can also just batch up
  several breaking changes at once (as v1.0.0 did) rather than needing its own
  standalone break to justify it -- but don't bump major for a release with zero
  breaking changes; that's what minor/patch are for.
- **MINOR** -- new functionality. Backward compatible by default; a breaking edge case
  is the exception, not the rule, and MUST be tagged `BREAKING:` in the CHANGELOG.md
  entry when it happens (see existing entries for the tag's exact form).
- **PATCH** -- bugfixes only, no intentional API change of any kind.

## Deprecating instead of breaking outright

Default posture: don't remove/rename/restructure a public API in one step. Deprecate
first, using the `deprecated` package (already a dependency) the codebase already uses
this way -- see `labfreed/pac_id_resolver/cit_v1.py`, `labfreed/pac_attributes/api_data_models/response.py`,
or `labfreed/pac_attributes/pythonic/py_attributes.py` for the existing pattern:

```python
from deprecated import deprecated

@deprecated("Use ResolverConfig")
class CITEntry_v1(LabFREED_BaseModel):
    ...
```

- The message should name the concrete replacement, not just say "deprecated" (compare
  the existing `"cit version 1 is deprecated. use resolvber config and load with
  ResolverConfig.from_yaml(s)"` -- name the actual replacement API/call).
- The deprecated path must keep *working*, not just exist -- delegate to the new
  implementation rather than leaving stale/rotting logic behind it.
- Keep it alive for **at least one more major version** after the one that introduced
  the deprecation, before actually deleting it. Track pending removals somewhere
  visible (e.g. a TODO.md entry: "remove `X`, deprecated since vN, earliest removal
  vN+1") so a deprecated symbol doesn't just get forgotten forever.
- Only actually delete a deprecated symbol at a MAJOR bump, and call the deletion out
  in that version's CHANGELOG entry.

## Picking the number itself

1. Classify every change since the last release (breaking / not / ambiguous, per above).
2. Pick the version bump from the highest-severity change present.
3. Update `__version__` in `labfreed/__init__.py`.
4. Add a `CHANGELOG.md` entry, tagging every breaking item `BREAKING:` regardless of
   whether the overall bump is major or minor.

## Alpha and beta pre-releases

Shipping in-progress work toward a not-yet-final version doesn't have to wait until
it's release-ready. Append a [PEP 440](https://peps.python.org/pep-0440/) pre-release
identifier directly to the target version -- no dot, no dash -- and publish that to the
*real* PyPI index like any other release:

- `1.0.0a1`, `1.0.0a2`, ... -- **alpha**: early, API may still shift.
- `1.0.0b1`, `1.0.0b2`, ... -- **beta**: feature-complete-ish, stabilizing toward the
  final version. This is the one actually in use -- the run of `1.0.0b1` through
  `1.0.0b44` (and counting) leading up to the still-pending `v1.0.0`.

Why publishing pre-releases straight to the real index (not just TestPyPI) is safe: PEP
440's version ordering means an unpinned `pip install labfreed` always resolves to the
latest *stable* release and silently skips pre-releases. Only someone who opts in with
`pip install --pre labfreed`, or pins the exact pre-release (`labfreed==1.0.0b44`), gets
it. Stable-channel users are never affected -- that's what makes this a nice mechanism
for getting in-progress work in front of early testers.

Mechanics -- alpha/beta and the final release use two different publish paths:
- **Alpha/beta**: bump only the trailing pre-release number (`b43` -> `b44`) in
  `labfreed/__init__.py`'s `__version__`, then publish directly from the `build_tools/`
  scripts (`publish.sh prod` / `publish.ps1 prod`) -- that runs `flit publish --repository
  pypi` straight to real PyPI from your machine, with no test gate in front of it.
- **Final release**: goes through `.github/workflows/pypi-publish.yml` instead, which
  fires when a GitHub Release is published. That pipeline runs the test suite
  (`pytest tests`) before it will publish -- so the actual gated path is the final
  release, not the pre-releases leading up to it. (Its `ruff check` step is currently
  non-blocking, `|| true` -- lint failures there don't stop a release.)
- Don't give each alpha/beta increment its own `CHANGELOG.md` heading. Accumulate the
  actual changes under the pending final version's heading (e.g. everything since
  `1.0.0b1` has been accumulating under `### v1.0.0`) and keep editing that one heading's
  content as work lands, rather than adding a `### v1.0.0b44` heading.
- To cut the real final release: drop the pre-release suffix (`1.0.0b44` -> `1.0.0`),
  finalize that heading's content, cut a GitHub Release (which triggers the
  test-gated publish above), and go through the full `release` skill checklist. A
  beta bump on its own does NOT need a README regen or a plugin sync -- only the final,
  suffix-dropped release does.

This is only the version-number part of cutting a release. For the full checklist
(regenerating README.md, syncing the public Claude Code plugin, design-choices/TODO
cross-links, final checks) see the `release` skill.
