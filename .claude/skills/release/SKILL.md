---
name: release
description: Checklist for wrapping a release of the labfreed package -- pick the version bump, regenerate README.md, and (this is the step it's easy to forget) sync the public Claude Code plugin in plugins/labfreed/ so its docs and code examples don't quietly drift out of date. Use whenever the user says to cut/wrap/prepare/ship a release, tag a new version, or publish a new version of the package.
---

# Wrapping a release

Composes four existing pieces -- don't re-derive their logic here, just don't skip any
of them:

1. **Version number** -- classify changes and pick MAJOR/MINOR/PATCH per the
   `versioning` skill; update `__version__` and `CHANGELOG.md` there.
2. **Deliver on deprecation promises** -- covered below. Only relevant when this
   release is a MAJOR bump; skip for MINOR/PATCH.
3. **README.md** -- regenerate via the `update-readme` skill
   (`build_tools/update_readme.py`), which re-executes `examples/examples.py` and
   copies in the new changelog.
4. **The public plugin** (`plugins/labfreed/`) -- covered below. This is the one that's
   easy to forget because nothing fails loudly when it goes stale: the package still
   works, tests still pass, only a *user of the plugin* would eventually notice Claude
   confidently suggesting an import path or API that no longer exists.

## Delivering on deprecation promises (MAJOR bumps only)

Every deprecation added under the `versioning` skill's policy carries an explicit "will
be removed in vN" promise in its own warning message, and is tracked in
`developer-docs/TODO.md`'s "Pending removals" section. A MAJOR release is the one place
that promise is cashed in -- it's silent, easy-to-forget cleanup work exactly like the
plugin sync below, so treat it with the same discipline:

1. Read `developer-docs/TODO.md`'s "Pending removals" section and find every entry whose
   "removed in vN" matches the version being cut (i.e. N equals this release's major
   number).
2. For each: delete the deprecated symbol/module (not just its `@deprecated`
   decorator/`warnings.warn` call -- the whole shim), confirm nothing left in this repo's
   `tests/` still exercises the old name, and remove its `TODO.md` entry.
3. Call out every deletion explicitly in this version's `CHANGELOG.md` entry (per the
   `versioning` skill's "only delete at a MAJOR bump, call it out in the changelog"
   rule) -- a silent removal is a breaking change users have no way to anticipate from
   the changelog alone.
4. An entry whose target version *hasn't* arrived yet (e.g. "removed in v3.0" while
   cutting v2.0) stays untouched -- don't remove early just because a major bump is
   happening.
5. If removing a symbol turns out to be unsafe (e.g. `labfreed-webtools` or another
   known consumer still imports it, per a cross-reference note in `design-choices.md`
   or `TODO.md`), don't remove it silently past its promised version either -- flag it
   to the user and decide deliberately whether to extend the deprecation window (update
   the warning message and `TODO.md` entry to the new target version) or proceed anyway.

This checklist is for a real, final release. A routine alpha/beta pre-release bump
toward a not-yet-shipped version is lighter-weight -- see the `versioning` skill's
"Alpha and beta pre-releases" section -- and does NOT need README regen or a plugin sync
on its own; those happen once, when the pre-release suffix finally drops.

## Syncing the public plugin

The plugin's whole value is that its code examples actually run. Every release that
changes anything import/API-shaped, re-verify it -- don't assume last release's content
still holds.

1. **Re-run `plugins/labfreed/skills/labfreed/references/quickstart.md`.** Execute every
   snippet against the just-bumped code (a plain script pasting each block in order is
   enough -- that's how this file was originally written and verified). Update any
   snippet whose imports, call signature, or shown output changed. If a snippet now
   errors, that's a real finding -- fix the snippet, don't just delete the example.
2. **Review `references/concepts.md`** for anything this release touched: PAC-CAT
   category tables, extension conventions, the PAC-ID Resolver/CIT terminology note,
   example issuers. Update or remove anything superseded.
3. **Review `SKILL.md`'s "Version note"** section. Replace it with *this* release's
   breaking changes (import path changes, renames, behavior changes) so someone reading
   it gets oriented to the current state, not last release's news. If there's been no
   breaking change since the last release, leave the note as-is rather than inventing
   one, but confirm it's still relevant instead of skipping the check.
4. **Decide whether the plugin needs its own version bump.** The plugin's
   `.claude-plugin/plugin.json` version tracks *plugin content* changes, not the
   package version -- bump it only if you actually changed something in step 1-3 above,
   using the plugin's own SemVer (a wording fix is a patch; a new/removed example
   section is at least a minor). Mirror the same version in this plugin's entry inside
   `.claude-plugin/marketplace.json`. If nothing in the plugin needed updating this
   release, say so explicitly and leave both versions untouched.

If a change was a real design decision (not just "we renamed a thing"), also check
whether it needs a `design-choices.md` entry -- see that skill.

## Before calling it done

- Run the full test suite (`python3 -m pytest tests/`) and read `git diff` on
  `README.md` and everything under `plugins/labfreed/` -- a clean run doesn't guarantee
  a clean diff (see `update-readme`'s notes on stale/non-deterministic output).
- If this release adds real functionality (not a pure patch/bugfix), run the
  `check-coverage` skill against whatever changed. Decide per finding whether to close
  the gap now or log it in `developer-docs/TODO.md` and ship anyway -- this is a
  judgment call each time, not a hard gate on every release.
- Publish by cutting a GitHub Release (tag = the dropped-suffix version) -- that's what
  triggers `.github/workflows/pypi-publish.yml`'s test-gated publish to PyPI. Don't use
  `build_tools/publish.sh`/`publish.ps1` for the final release; those bypass the test
  gate and are meant for the alpha/beta bumps leading up to it (see `versioning`).
- Know which branch the marketplace is actually served from. `/plugin marketplace add
  owner/repo` (no `@ref`) resolves to the repo's **default branch on GitHub** -- check
  `git remote show origin` or the repo settings rather than assuming it's `main`; at
  last check this repo's default was `dev`, not `main`. If the marketplace is meant to
  track releases only, either pin installs to `@main` explicitly when documenting the
  install command, or get the plugin/marketplace changes merged to whichever branch is
  actually the GitHub default -- don't let "it's on `dev`" and "we told people to add
  the marketplace unpinned" quietly disagree with each other.
