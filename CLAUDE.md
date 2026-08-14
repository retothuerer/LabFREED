# CLAUDE.md

Instructions for Claude Code (or any AI agent) working in this repository.

## No commit is ever made in the repo owner's name without explicit, real-time approval

The git identity configured for this repo (`retothuerer` / the repo owner's real GitHub
identity) is the only identity available here — there is no separate "Claude" author.
Any commit created in this working tree is indistinguishable in `git log` from one the
owner typed themselves, so provenance depends entirely on process, not on what git records.

**Rules:**

1. **Never run `git commit` or `git push` yourself, ever — both are the owner's to
   execute.** For a commit: stage the intended files (`git add`) and draft the commit
   message, then hand both to the owner and let them run `git commit` themselves. For
   pushing: once commits exist locally, ask whether to push, but even a "yes, push" only
   covers that one push — don't run it proactively otherwise, and don't assume the owner
   wants Claude to run it at all (the owner has said outright they'll push it themselves).
   Approving a plan, a phase, or an option that merely *mentions* committing or pushing
   (e.g. picking "update docs, test, commit standalone" from a list of choices) is NOT
   approval to run `git commit`/`git push` — that approval covers the approach, not the
   act, and the act is the owner's alone to perform.
   **Always display the drafted commit message inline in the chat response itself** -
   not just written to a scratch file with the path mentioned. A file is fine *in
   addition* (e.g. for `git commit -F`), but the owner should be able to read the actual
   message text without opening anything else.
2. **Never create branches or worktrees on your own initiative** — not via a direct
   `git branch` / `git worktree` command, and not implicitly through agent/workflow
   tooling that isolates work in a new worktree (e.g. `isolation: "worktree"`). Operate
   on the current checkout/branch unless the owner explicitly asks for a new one.
3. **Never reference Claude, Claude Code, or any AI agent in a commit message** — no
   `Co-Authored-By: Claude` trailer, no mention in the subject or body. The owner does
   not want commits attributed to or associated with an agent in any way, in message
   content or trailers. If agent involvement needs to be recorded for later provenance
   checks, do that outside the commit itself (e.g. a session note), never inside it.
4. **Watch for environment-level auto-commit.** This kind of sandbox has been observed to
   silently commit — and push to the real GitHub remote — a dirty working tree with the
   message "." (e.g. triggered by a `git checkout -b` or branch switch), without any
   explicit `git commit`/`git push` call. After any checkout, branch switch, or similar
   operation, run `git status` and `git log --oneline -3` and compare against
   expectations before doing anything else. If an unexplained commit appears, check
   whether it already reached `origin` (`git fetch`, then compare `git rev-parse
   origin/<branch>` against local) and flag it to the owner immediately — never assume
   it's benign just because the content looks correct.
5. **Never use destructive or history-rewriting git operations** (`push --force`,
   `reset --hard`, amending an already-pushed commit, interactive rebase, `--no-verify`)
   without an explicit request.

If any of the above is unclear in a given situation, stop and ask rather than guessing.

## `PacInfo` is the data-prep layer, not the UI

`PacInfo` (`labfreed/labfreed_extended/app/pac_info/pac_info.py`) is meant to be the
single place that resolves and normalizes attribute data for consumption elsewhere -
looking up well-known keys, extracting codes out of raw values, applying static
lookups (e.g. GHS statement text), deciding which of several possible representations
(bare code vs. supplier-delivered text, attribute value vs. resource link) wins.

UI/template layers (`pac_issuer_lib`, `labfreed-webtools`, etc.) should consume
already-prepared `PacInfo` properties (`signal_word`, `hazard_statements`, `supplier`,
...) rather than looking up or parsing attributes themselves. A template reaching for
`find_attributes()` or a raw well-known key directly should be the exception (e.g. a
field with no dedicated `PacInfo` property yet), not the default - if a UI layer needs
to parse/resolve attribute data itself, that logic almost always belongs in `PacInfo`
instead, so every consumer gets it for free.

## LabFREED has no unitless numbers

Every numeric value carries a unit - LabFREED is for labs, and a bare number without
one is unusable/dangerous there. `Quantity(value, unit=None)` is the one sanctioned way
to represent a genuinely dimensionless value (e.g. GS1/UNECE `C62`, "one"/count) - an
explicit, intentional choice, not a silent default. Convenience construction from a bare
`int`/`float` is fine at call sites that need it (e.g. T-REX's numeric segment
handling), but it must immediately wrap the value in `Quantity(..., unit=None)` and warn
that this happened silently, rather than leaving a bare number floating around
un-wrapped or defaulting to unitless without flagging it. The warning lives once, in
`Quantity` itself (fires whenever its normalized `unit` ends up `None`) - not
re-implemented at every call site that happens to construct one. Examples/docs should
model the explicit-`Quantity` form, with a comment noting that a bare `int`/`float` is
accepted for convenience but discouraged - never present the bare form as the norm.

## Repo structure map

Use this to jump straight to the right place instead of grepping the whole tree cold.

- `labfreed/pac_id/` — PAC-ID core implementation
- `labfreed/pac_cat/` — PAC-CAT (categorized PAC-ID) implementation
- `labfreed/pac_id_resolver/` — PAC-ID Resolver: `resolver.py` + `services.py`
- `labfreed/pac_attributes/` — PAC-ID Attributes: `api_data_models/`, `client/`, `server/`, `pythonic/` (the IRI migration work lives here)
- `labfreed/trex/` — T-REX serialization, with a `pythonic/` convenience layer
- `labfreed/qr/` — QR code generation/reading for PAC-IDs
- `labfreed/well_known_keys/` — key registries split by namespace: `gs1/`, `labfreed/`, `unece/`
- `labfreed/well_known_extensions/` — extension definitions layered on well-known keys
- `labfreed/labfreed_extended/` — higher-level app layer (`app/`, `pac_issuer_lib/`) built on the core building blocks
- `labfreed/labfreed_experimental/` — not-yet-stable features (`actions/`, `pac_disco/`)
- `labfreed/utilities/` — shared helpers used across the above
- `tests/` — mirrors the package layout: `test_PAC_ID/`, `test_PAC_CAT/`, `test_TREX/`, `test_resolver/`, `test_attributes/`, `test_actions/`, `test_de_serialization_incl_extension/`, plus `generated_tests/`
- `examples/` — runnable usage examples, incl. `attribute_server/` and `pac_mettorius_com/`
- `developer-docs/` — `design-choices.md` (decision log, see the `design-choices` skill), `TODO.md` (backlog)
- `build_tools/` — scripts incl. `update_readme.py` (see the `update-readme` skill)
- `plugins/labfreed/` — the public Claude Code plugin synced at release time (see the `release` skill)
- `spec_versions.yaml` — pinned spec commits checked by the `check-spec-conformance` skill
- `plans/` — in-flight implementation plans (e.g. the IRI migration)

Repo-specific skills already cover the workflows for most of the above — check `.claude/skills` before hand-rolling a process (versioning, release, test-first, design-choices, update-readme, check-spec-conformance, small-fix).

## Troubleshooting / token discipline

When something isn't working, don't burn tokens on trial-and-error:

- After ~2 failed attempts at the same fix, stop retrying variations. Either read the actual error/root cause directly (full traceback, the specific failing assertion) instead of guessing again, or ask the user.
- Don't rerun a large test suite or build just to re-read output already captured — grep/tail the existing output first.
- Don't keep spawning fresh Explore/search agents with slightly reworded queries if the first one came back empty or wrong — narrow the query (specific file/symbol) or ask instead of broadening and retrying.
