# Developer documentation & setup

This folder is for humans (developer/supervisor) working on this repo, including
alongside Claude Code. It's separate from [`docs/`](../docs), which is generated API
reference output (`pdoc`) - don't put hand-written content there, it gets regenerated.

## Setup

```bash
pip install flit
flit install --deps develop
# or: pip install -e ".[dev]"
```

Requires **Python 3.11–3.13**. Python 3.14 breaks pydantic's evaluation of
`float | int`-style forward refs, surfacing as
`TypeError: unsupported operand type(s) for |: 'property' and 'type'`. This currently
breaks *collecting* three test files - not a code bug, don't try to fix it in the
package:

```bash
pytest --ignore=tests/test_Quantity.py --ignore=tests/test_attributes --ignore=tests/test_sanity_check.py
```

If you're on 3.11–3.13, plain `pytest` is fine. CI (`.github/workflows/run-tests.yml`)
runs on 3.11.

## Branches

- `main` - releases only.
- `dev` - active development / integration branch.
- Larger efforts get their own feature branch off `dev` (e.g. `pac-cat-improvements`),
  merged back into `dev` when done.

**This repo is sometimes worked on by more than one Claude Code session at once**
(different windows/agents on the same task, or overlapping tasks). Before assuming a
clean working tree or trusting a previous session's summary of "what's done": run
`git status` and `git log --oneline -10` yourself. Uncommitted changes you didn't expect
are more likely someone else's in-progress work than a mistake - don't discard them
without checking first.

## Working with Claude Code here

Available project skills, in `.claude/skills/`:

- **`test-first`** - the default way to add tests: one reviewable unit (test, or a
  closely-related/parametrized group) at a time, flagged
  `@pytest.mark.skip(reason="NOT REVIEWED")` until you delete that line yourself. Run
  `grep -rn 'NOT REVIEWED' tests/` any time to see everything still pending your review.
  No implementation change should land for behavior that's only covered by a still-skipped
  test - see the skill for how to deliberately override that (e.g. "implementation-first
  for this bit").
- **`check-spec-conformance`** - compares the Python implementation of a building block
  (PAC-ID, PAC-CAT, PAC-ID-Resolver, PAC-Attributes, T-REX) against its spec repo, using
  the pinned commit in [`spec_versions.yaml`](../spec_versions.yaml) to detect drift since
  the last check.
- **`update-readme`** - regenerates README.md's examples/changelog sections via
  `build_tools/update_readme.py`. Needs network access to `mettorius.com` for one example
  (resolver) - if that example errors with "No Internet Connection" in a devcontainer,
  it's usually stale DNS from container start, not a real outage; restart the container.
- **`design-choices`** - documents non-obvious architectural/API decisions (with the
  rejected alternatives and why) in [`design-choices.md`](design-choices.md). Use it
  whenever a decision at that level gets made or investigated, not for routine
  implementation notes.

## Design choices

[`design-choices.md`](design-choices.md) is the log of non-obvious architectural/API
decisions in this codebase - why something is built a certain way, when that reasoning
isn't obvious from reading the code alone. See the `design-choices` skill above for
when/how to add to it.

## TODO

[`TODO.md`](TODO.md) is the general developer backlog - not limited to design-choice
follow-ups, though those cross-link into `design-choices.md` when relevant. Anything
worth not losing track of goes here rather than only living in chat history.

## Spec conformance

[`spec_versions.yaml`](../spec_versions.yaml) pins the exact spec-repo commit each
building block's implementation was last checked against, plus notes on what was found
and fixed. Treat entries there as a snapshot, not necessarily current - a spec repo (e.g.
`ApiniLabs/PAC-CAT`) can gain commits after the pin date, and this file is only updated by
running the `check-spec-conformance` skill again. **When comparing implementation to
spec, check which branch of the spec repo the work you're comparing against actually
targets** - spec repos often have a WIP branch ahead of both `main` and the published
spec on labfreed.org; treat those as pre-spec/experimental unless told otherwise.

## Tests

- `pytest` from repo root (`pytest.ini` sets `pythonpath = .`).
- New tests: follow the `test-first` skill above by default.
- `PAC_CAT.from_url(url, suppress_validation_errors=True)` is the standard test helper
  pattern for parsing a URL without raising on validation errors - see any file under
  `tests/test_PAC_CAT/` for the idiom.
