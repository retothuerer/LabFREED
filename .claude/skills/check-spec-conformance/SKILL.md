---
name: check-spec-conformance
description: Compare the labfreed Python implementation of a building block (PAC-ID, PAC-CAT, PAC-ID-Resolver, PAC-Attributes, T-REX) against its specification repo, using a pinned commit in spec_versions.yaml to detect what changed since the last check. Use whenever the user asks to check/compare/audit the implementation against the spec(s), asks whether a spec changed since it was last checked, or asks to run a spec-conformance pass.
---

# Check spec conformance

Compares this repo's implementation of a building block against its spec, and
tracks *which version of the spec* was last checked so repeat runs don't
re-read everything from scratch.

## The pin file: `spec_versions.yaml`

Lives at the repo root. One entry per building block:

```yaml
PAC-ID:
  repo: https://github.com/ApiniLabs/PAC-ID
  branch: main
  commit: <sha>       # null if never checked -- always do a full pass in that case
  checked_on: "YYYY-MM-DD"
  notes: >
    Free text: what was found/fixed last time, and any gap that was found but
    deliberately NOT addressed (so it isn't re-reported as new every run).
```

Read this file first. It tells you the last commit the implementation was
verified against, and — via `notes` — what's already a known, accepted gap.
Don't re-report something already recorded in `notes` as intentionally
deferred; just confirm it's still the case if it's relevant to what changed.

## Step 1: locate the local spec clone

Do not assume a fixed path — local clone folder names have changed before in
this environment (e.g. `PAC-ID` became `Specs: PAC-ID`). Find the right
directory by matching the `repo` URL in `spec_versions.yaml` against `git
remote -v` output across plausible workspace roots, e.g.:

```bash
for d in "/workspace"/*/ ; do
  git -C "$d" remote -v 2>/dev/null | grep -qi "ApiniLabs/PAC-ID" && echo "$d"
done
```

## Step 2: check what changed since the pin

```bash
cd <spec repo>
git fetch origin
git rev-parse origin/<branch>
```

- If this matches the pinned `commit` → nothing changed. Report that and stop.
- If `commit` is `null` → no prior check exists. Do the **full pass** (Step 4).
- Otherwise, diff the two:

```bash
git diff --stat <pinned commit>..origin/<branch>
```

## Step 3: classify the diff — shortcut or full pass?

Look at the changed file list from Step 2.

**Shortcut path** applies only if *every* changed file is a well-known
key/type reference table — filenames like `well-known-id-segment-keys.md`,
`well-known-extension-types.md`, `well_known_keys.md`, or equivalent
per-building-block lookup tables. These are markdown tables mapping a code to
a meaning; changes to them are additive data, not grammar/normative changes.

If anything else changed (README.md, faq.md, any spec section describing
structure/grammar/validation rules) → **full pass**, even if a well-known-keys
file also changed alongside it.

### Shortcut path

1. `git diff <pinned>..<current> -- <the well-known-*.md file>` to see exactly
   which keys/types were added, removed, or reworded.
2. Find the mirrored Python list/enum/dict in the implementation (e.g.
   `labfreed/well_known_keys/labfreed/well_known_keys.py`'s `WellKnownKeys`
   enum for PAC-ID segment keys, or `default_extension_interpreters` for
   extension types) and bring it in sync.
3. Add/update a small test asserting the new entries are recognized (e.g. that
   a segment using the new key no longer gets a "not well known" RECOMMENDATION).
4. Update the pin (Step 5). Skip the rest of this skill — no need to re-read
   the whole spec or implementation.

### Full pass

This is the expensive, thorough path — same methodology used for the first
PAC-ID conformance pass (2026-07-27):

1. **Read every spec doc for the building block, completely** — not just the
   README; also `faq.md`, `text-format.md`, `well-known-*.md`, and any other
   files in that spec repo. Small satellite files often carry MUST-level rules
   the main README only references.
2. **Read every corresponding implementation file, completely.**
3. **Cross-reference every MUST / MUST NOT / SHOULD / SHOULD NOT / RECOMMENDED
   clause** in the spec against the implementation. For each one, is it
   validated, and at the right severity (ERROR for MUST, RECOMMENDATION for
   SHOULD)? Missing validators are as much a finding as wrong ones.
4. **Empirically verify every suspected gap before reporting it** — a two-line
   Python snippet constructing the offending case and checking the result.
   Static reading is not enough; this is how the extension-parsing
   `AttributeError` (3rd+ unnamed extension) and the bare-`ValueError` crash
   (colon inside an id segment value) were actually confirmed, not just
   suspected.
5. **Prioritize findings**: crashes / raised exceptions that break the
   library's normal non-throwing validation contract first, then missing
   MUST-level (ERROR) checks, then missing SHOULD/RECOMMENDED checks, then
   style/consistency nits last.
6. **Propose fixes**, prefer minimal, additive changes consistent with the
   existing validation architecture (`LabFREED_BaseModel._add_validation_message`,
   never raise for a spec-validity issue — see `labfreed_infrastructure.py`).
7. **Write a test per fix** reproducing the gap, placed next to the existing
   tests that already cover that area (don't create a parallel test file
   structure if one already covers that code path).
8. **Run the full test suite** (`python3 -m pytest tests/`) before and after —
   note known-broken, unrelated pre-existing failures (check
   `.claude/skills/update-readme/SKILL.md` for ones already documented, e.g.
   the Python 3.14 / pydantic forward-ref issue) so they aren't misattributed
   to this pass. If the working tree already has unrelated uncommitted changes
   (someone else's concurrent work-in-progress), a failing test caused by
   *those* is not this skill's problem to fix — say so plainly rather than
   trying to patch around it.
9. Note explicitly, in the final report and in the pin's `notes`, any gap
   found but *not* fixed, and why (e.g. it needs a larger design decision, or
   it's already tracked elsewhere, e.g. `plans/*.md`).

## Step 4: update the pin

After either path, update that building block's entry in `spec_versions.yaml`:
`commit` → the new HEAD, `checked_on` → today, `notes` → a short summary of
what was found/fixed and what was deliberately left alone.
