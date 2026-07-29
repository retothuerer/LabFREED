# CLAUDE.md

Instructions for Claude Code (or any AI agent) working in this repository.

## No commit is ever made in the repo owner's name without explicit, real-time approval

The git identity configured for this repo (`retothuerer` / the repo owner's real GitHub
identity) is the only identity available here — there is no separate "Claude" author.
Any commit created in this working tree is indistinguishable in `git log` from one the
owner typed themselves, so provenance depends entirely on process, not on what git records.

**Rules:**

1. **Never run `git commit` yourself, ever — and never run `git push` unless the owner
   has explicitly asked for it in that specific moment.** For a commit: stage the
   intended files (`git add`) and draft the commit message, then hand both to the owner
   and let them run `git commit` themselves. Approving a plan, a phase, or an option that
   merely *mentions* committing (e.g. picking "update docs, test, commit standalone" from
   a list of choices) is NOT approval to run `git commit` — that approval covers the
   approach, not the act, and the act is the owner's alone to perform.
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
