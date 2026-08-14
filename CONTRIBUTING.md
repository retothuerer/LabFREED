# Contributing

Thanks for considering a contribution to this repo, the Python reference implementation
of the [LabFREED](https://labfreed.org/) building blocks (PAC-ID, PAC-CAT, T-REX,
PAC-ID Resolver, PAC-ID Attributes).

## Reporting bugs / requesting features

Open a [GitHub issue](https://github.com/retothuerer/LabFREED/issues). For a security
vulnerability, see [SECURITY.md](SECURITY.md) instead of filing a public issue.

## Development setup

Requires Python 3.14.

```bash
pip install flit
flit install --deps develop
# or: pip install -e ".[dev]"
pre-commit install
```

`pre-commit install` wires up Ruff and basic hygiene checks (trailing
whitespace, YAML/TOML validity, etc.) to run automatically before each
commit — the same checks CI runs, so issues surface locally first.

## Running tests

```bash
pytest
```

CI (`.github/workflows/run-tests.yml`) runs the same suite on Python 3.14.

## Code style

This project uses [Ruff](https://github.com/astral-sh/ruff) (config in `pyproject.toml`,
line length 100). Run `ruff check .` before submitting — CI enforces it (blocking) in both
`run-tests.yml` and `pypi-publish.yml`, and `pre-commit` runs it locally before each commit
if installed (see Development setup above).

## Dependency scanning

`.github/workflows/dependency-scan.yml` runs `pip-audit` (known CVEs) and `pip-licenses`
(dependency license report) on every PR, on a weekly schedule, and on demand. Both are
report-only for now — check the workflow run if you're adding a new dependency, but a
finding there won't block your PR yet.

## Branches

- `main` — releases only.
- `dev` — active development / integration branch. Base feature branches off `dev`, not
  `main`.

## Making changes

- Keep pull requests focused — one logical change per PR.
- Add or update tests for any behavior you change.
- If a change renames/removes/restructures anything importable from `labfreed`, or
  changes a method's signature or observable behavior, see the versioning policy in
  [README.md](README.md#versioning) — public API changes need a deprecation path, not an
  instant break, while the package is pre-1.0.
- Add a bullet to the top (unreleased) section of `CHANGELOG.md`. It's folded into
  `README.md`'s changelog automatically as part of the release process.

## Spec conformance

If a change touches behavior defined by one of the LabFREED specs, check it against the
spec repos under [github.com/ApiniLabs](https://github.com/ApiniLabs) — `spec_versions.yaml`
at the repo root pins the last-checked commit and notes for each building block, though
treat it as a snapshot rather than necessarily current.

## More detail

`developer-docs/README.md` has more on the repo's internal conventions (design-choices
log, TODO backlog, test-writing conventions) if you want the fuller picture before a
larger contribution.
