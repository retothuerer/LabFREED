---
name: check-coverage
description: Run test coverage for the labfreed package, triage the gaps that are actually worth closing, and propose new tests for them (test-first: skip-marked, pending review). Use whenever the user asks to check/analyze/improve test coverage, asks "what's not tested," wants coverage numbers raised, or as a pre-release health check.
---

# Checking coverage and proposing tests

Coverage numbers are a starting point for triage, not a target to maximize. This skill
is about finding real, worth-closing gaps and proposing tests for exactly those - not
chasing 100% or writing a test for every red line a tool shows you.

## Step 1: run coverage

```bash
pytest --cov=labfreed --cov-report=term-missing --cov-report=html
```

If `pytest-cov` isn't installed, `pip install pytest-cov` and make sure it's actually
declared in `pyproject.toml`'s `dev` extra (not just installed ad hoc in this session) -
same reasoning as the `test-first` skill's note on test-only dependencies: CI installs
from `pyproject.toml`, not from whatever happens to already be in this venv.

`term-missing` gives per-file % plus the exact missing line numbers - that's the thing
to actually read, not just the percentage column. `htmlcov/index.html` is useful for
browsing source with lines highlighted, but isn't required for the analysis below.

## Step 2: triage - pick files worth investigating

Don't process every uncovered line in the repo. Compare each file's % against the
overall average and look for files noticeably below it, or files that are new/recently
changed and still thin. If the user named specific files or areas, start there instead
of re-deriving a list yourself.

For each candidate file, **read the actual missing line ranges** in context (the
function/method they belong to), grouped by function - not as a flat list of numbers.
A raw line-number list tells you nothing about what behavior is actually untested; the
surrounding code does.

## Step 3: for each gap, decide real gap vs. dead code

Before writing a test for a missing branch, ask whether it's actually reachable through
realistic use of the public API. Signs a branch is dead/leftover rather than a genuine
gap:

- Reaching it needs reflection tricks, `sys.modules` manipulation, module reloads, or
  calling a private method with input no public caller could ever construct.
- It's an `except` around a call whose wrapped code structurally can't raise that
  exception type (e.g. catching a `requests` exception inside a purely in-process
  callback that never makes an HTTP call).
- It's leftover manual-run code (`if __name__ == '__main__':` blocks and similar).
- An upstream validator already rules out the input that would be needed to reach it,
  as far as you can tell from reading that validator.

Don't invent a contrived test just to paint a line green. Instead, flag it as a
candidate dead-code finding in `developer-docs/TODO.md` (short entry, file:line
reference, why it looks unreachable) so it doesn't get silently rediscovered as a
mystery later, and move on. If you're not sure whether something is a real gap or dead
code, say so and ask rather than guessing either way.

## Step 4: reuse existing test patterns

`tests/` mirrors `labfreed/`'s package layout. Before writing a new test file, find
whatever test file already exists for that unit and read it first - its fixtures,
mocking style (`monkeypatch`, `unittest.mock.patch`, in-memory construction via
`tmp_path`, hand-rolled fakes/doubles), and naming conventions are the pattern to follow,
not something to reinvent. Extend an existing file for a unit that already has one;
only create a new file when none exists yet for that unit.

## Step 5: enums need a different question, not "is it covered"

`coverage.py` marks an `Enum`'s `MEMBER = "value"` lines covered the instant the module
is *imported* - regardless of whether anything ever actually reads that member. A
100%-covered enum file is not evidence the enum is exercised; a 0%-covered one usually
means the module (and therefore the enum) is never imported by anything at all, which is
a different, real finding worth surfacing on its own (an orphaned/unwired module), not
just a coverage gap.

Given that, don't propose a test that just re-asserts an enum's own key/value mapping
when the enum is an open-ended lookup/key registry (well-known-keys style, can grow
indefinitely) - that only replicates the enum definition and adds no real assurance.
DO propose an exhaustive membership test (`assert {m.value for m in TheEnum} ==
{...}`) when the enum is a small, closed set that encodes state/status/severity - there,
"exactly these values and no others" is a real invariant that consuming code (branches,
`match` statements) actually depends on. If it's unclear which bucket a given enum falls
into, ask rather than assuming.

## Step 6: write the tests, test-first

Every new test follows the `test-first` skill: `@pytest.mark.skip(reason="NOT
REVIEWED")` directly above it, `import pytest` if not already imported, and a sentence
before the code saying what the test (or group) covers.

Because skip-marked tests never execute, running the suite afterward can't confirm
they're actually correct - it only confirms they're collected and skipped. Independently
verify each test's assertions against the real, current code before presenting it (e.g.
a throwaway script that runs the same calls unskipped) rather than handing over a
plausible-looking but unverified test. This matters more here than in ordinary
test-first work, precisely because "run it and see" isn't available as a check.

## Step 7: present a triage summary, don't just start writing

When there's more than one reasonable scope (which files, whether to also test enums
that are already at 100% by the metric, how to handle borderline-dead branches), that's
a judgment call for the user, not something to resolve by picking the most thorough
option yourself. Summarize what was found - grouped by file/function, with the real vs.
dead-code split already made - and ask before writing a large batch of tests, the same
way you would before any other multi-file change.

## Using this from the `release` skill

The `release` skill's "Before calling it done" step can point here: for any release that
adds real functionality (not a pure patch/bugfix), run this skill against whatever
changed and decide - close the gaps now, or log them in `developer-docs/TODO.md` and
ship anyway. It's a judgment call each time, not a hard gate on every release.
