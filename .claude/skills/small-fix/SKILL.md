---
name: small-fix
description: Restrict search/read/edit scope to whatever specific file or folder the user pointed to (e.g. labfreed/, labfreed/labfreed_extended/, labfreed/labfreed_experimental/, a single file, or a specific tests/ subfolder) for a change the user explicitly calls a small fix. Never escalates above that pointed-to level on its own - asks before widening scope instead. Does not proactively update tests/docs/changelog while in this scope - flags drift instead of fixing it. Use ONLY when the user explicitly calls the current task a small fix - never infer this from diff size or your own judgment.
---

# Small-fix local scope

Default posture for this repo is full-repo awareness. This skill narrows that for one task at a time — but only when the user explicitly asked for it.

## Trigger

Only when the user explicitly labels the current task a "small fix" (or unambiguous equivalent) in the request itself. Never infer it from:
- the apparent size of the diff once you've looked
- your own judgment that a change "should" be small
- an earlier task in the conversation being labeled that way — each task needs its own explicit label

If it's unclear whether a new request is meant to inherit an earlier "small fix" label, ask rather than assume either way.

## What "local scope" means

- There's no hardcoded default folder (not even `labfreed/`). The scope is exactly the file or folder the user pointed to when describing the small fix — that could be a single file, a subpackage like `labfreed/labfreed_extended/` or `labfreed/labfreed_experimental/`, the whole `labfreed/` package, a specific `tests/` subfolder, or anything else — whatever level they named.
- Stay at or below that level. Don't move up to the parent directory, a sibling folder, or the repo root on your own initiative — even if the target isn't found there.
- If what you're looking for isn't within the pointed-to scope, silently escalate to the level ..LabFREED/any/subfolder but ask befor eescalating further

## Keeping docs/tests in sync — don't do it automatically

Keeping tests, the CHANGELOG, README, and design-choices.md in sync with a code change is normally good practice. Under this skill, don't do that expansion as a side effect of a small fix:

- If the fix looks like it should also touch a test, the CHANGELOG, or a doc, say so and ask — don't edit them yourself.
- The point of calling something a "small fix" is to keep the blast radius small and predictable. Silently pulling in doc/test updates defeats that, even when those updates would themselves be correct.

## Why

LabFREED is the largest, but also the most well-structured, repo in this workspace, with clean boundaries at every level — `labfreed/` vs. `tests/`/`examples/`/`developer-docs/`/`docs/`/`plugins/`/`plans/`, and inside `labfreed/` itself, subpackages like `labfreed_extended/` and `labfreed_experimental/` vs. the core building blocks. Whichever level the user points to for a small fix, staying inside it — and asking rather than assuming when it's not enough — keeps the blast radius exactly as small as intended. See the repo's `CLAUDE.md` for the general troubleshooting/token-discipline notes this complements.

## Exiting

No explicit exit needed — the label applies only to the task it was said for. The next request without an explicit "small fix" label goes back to normal full-repo scope.