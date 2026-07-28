---
name: design-choices
description: Document non-obvious architectural/API decisions in developer-docs/design-choices.md, with the rejected alternatives and why. Use whenever a design choice at this level gets made, discovered, or investigated - e.g. deciding between a built-in feature and rolling custom code, or explaining why the code is shaped a certain way when that reasoning isn't obvious from reading it. Also covers cross-linking into developer-docs/TODO.md (the general dev backlog, not design-choices-specific) for follow-up ideas spawned while documenting a choice.
---

# Documenting design choices

`developer-docs/design-choices.md` records *why* something in this codebase is built a
certain way, for decisions that aren't obvious from the code alone - "why we built X
instead of using the framework's Y," "why we didn't do the obvious thing here," "we
investigated Z and decided against it, here's why." Keep entries at that flight level: a
deliberate tradeoff with a real rejected alternative - not "we used a dict here."

## When to add an entry

- Right after resolving a "should we use the built-in X or roll our own" question -
  document it whichever way it lands. "We checked and the built-in is fine, no need for
  custom code" is as worth recording as "we rolled our own, here's why."
- When explaining a non-obvious existing design decision that isn't captured anywhere
  else yet.
- When investigating whether a library/language feature could replace custom code: the
  investigation itself - what was verified empirically versus assumed - is the valuable
  part, independent of the outcome.

## Format

Each entry: a short title, then **Decision**, **Why**, **Alternatives considered / why
not**, and optionally **Impact**. Name the actual API or pattern considered for each
alternative, and say what was verified (tested / read source) versus assumed. End with
`_Investigated <date>._` so staleness is visible later.

## Follow-up ideas

If documenting a choice surfaces a "we could revisit this later if X" idea that isn't
worth acting on now, add it to `developer-docs/TODO.md` - the general developer
backlog, not a design-choices-specific file - and cross-link both directions (the TODO
entry links back to the design-choice section; the design-choice entry links forward to
the TODO section).
