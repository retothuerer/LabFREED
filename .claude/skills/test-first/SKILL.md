---
name: test-first
description: Test-first workflow where new tests are flagged unreviewed via @pytest.mark.skip until the user manually removes the marker, edits to an already-reviewed test re-flag it too, and implementation changes wait for a reviewed test to exist first. Use whenever the user says to work test-first, asks for a test before implementing, or invokes this skill directly.
---

# Test-first development workflow

Default posture for the whole loop: **no implementation change without a reviewed test
driving it.** "Reviewed" has one specific meaning here - the human deleted the
`@pytest.mark.skip(reason="NOT REVIEWED")` line themselves. Nothing else counts.

## Writing tests

There's no rule limiting this to one test at a time - the skip marker (below) is what
actually provides the review tracking, not the pace of writing. Write as many tests
together as make sense.

What's worth watching for instead: don't sink a lot of effort into a big pile of tests
built on a misunderstanding from the start - that's wasted work for both of you. So
group tests that genuinely test something related (a pass/fail pair, a few boundary
values, variations on one behavior), and if you're building on an assumption you're not
sure about, check in rather than grinding through a lot of tests first.

`@pytest.mark.parametrize` is one option for cutting duplication across similar cases,
not a rule. It's a real tradeoff: a parametrized test can be harder to read at a glance,
since "what is this actually testing" ends up split between the function body and the
parameter list. If a good, natural name for the parametrized test starts feeling forced
or generic, that's the signal to just write separate tests instead rather than force
the cases together.

Say in a sentence or two what a test (or group of tests) covers before showing the code,
so the human knows what they're about to look at.

## Mark it unreviewed

Directly above each test function:

```python
@pytest.mark.skip(reason="NOT REVIEWED")
def test_something():
    ...
```

- Add `import pytest` to the file if it isn't already imported.
- The reason string is always exactly `"NOT REVIEWED"`, verbatim - never a custom
  per-test message. That makes `grep -rn 'NOT REVIEWED' <test dir>` a complete, accurate
  backlog of everything still pending, with no separate tracking file needed.
- One decorator above a parametrized function skips/unskips every case together - don't
  try to mark individual parameter cases separately.

## Editing an already-reviewed test

If you change the body or assertions of a test the human had previously reviewed
(i.e. they'd deleted its skip marker), put the marker back:

```python
@pytest.mark.skip(reason="NOT REVIEWED")
def test_something():
    ...
```

Their review covered *that* version of the test, not whatever it becomes after your
edit - re-flagging it means the new version goes through the same gate before anything
is implemented against it.

- Only applies to changes *you* make. If the human edits a test themselves, that edit is
  inherently reviewed - they wrote it - don't add the marker to it.
- Doesn't apply to adding a brand-new test alongside already-reviewed ones in the same
  file - only the new test needs the marker; leave the existing, still-valid tests alone.

## Stop and wait

- The human reviews each test as code and decides whether its assertions actually
  capture the intended behavior. Deleting the skip line *is* that review action - never
  remove it on their behalf, even if you're confident the test is correct.
- Don't touch implementation code for behavior that's only exercised by a still-skipped
  test - see the mode-switching exception below for the one deliberate way around this.

## Why `skip`, not `xfail`

`skip` never executes the test body -> reports `SKIPPED`, never confusable with a real
`FAILED`. `xfail` executes the test and reports `xfail`/`XPASS` instead, which conflates
two things that must stay separate: *has a human reviewed this* (what we're gating on)
and *does the code currently satisfy it* (an orthogonal fact - a correct-but-unreviewed
test can already be passing, or can be failing because nothing implements it yet).
`xfail` blurs exactly that distinction; `skip` keeps "reviewed?" a pure gate with zero
signal about the code underneath.

## Switching modes

- Default is test-first, always, unless one of the two overrides below is explicitly in
  effect.
- **One-off override** ("let's prototype this first", "implementation-first for this
  bit"): applies only to that piece of work. Once it settles, resume the normal loop -
  propose a reviewed test for it before extending it further, and say that's what you're
  doing.
- **Standing override** ("switch to implementation-first mode", or comparably explicit):
  session-wide, stays in effect until the human says to switch back.
- Never infer a standing switch from a single one-off request. If it's ambiguous which
  was meant, ask rather than guess.

## Practical notes

- Mention skip/fail counts in test output only if not already obvious from context -
  don't narrate every run.
- To reconstruct where a review session left off: `git status`/`git diff` on the test
  file, plus a grep for the marker. That's the whole state - nothing else to track.
- If a test imports a third-party package that isn't already a dependency anywhere in
  pyproject.toml, add it to the `dev` group there. GitHub Actions runs the test suite
  when publishing a release of labfreed, so a test-only dependency missing from
  pyproject.toml passes locally (if the package happens to be installed) but breaks the
  release build. Fixtures/helpers that ship inside a package already listed (e.g.
  `monkeypatch`, bundled with `pytest`) don't need a separate entry.
