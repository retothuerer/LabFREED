---
name: labfreed
description: Reference and code quickstart for the LabFREED Python package (PyPI `labfreed`) -- PAC-ID, PAC-CAT, T-REX, PAC-ID Resolver, PAC-ID Attributes. Use whenever writing, reviewing, or debugging Python code against this package, or explaining what PAC-ID / PAC-CAT / T-REX / CIT / PAC-ID Attributes are. These terms are unique to this ecosystem, not generic English -- trigger on a bare mention of any of them even if "LabFREED" itself never comes up.
---

# LabFREED (Python)

LabFREED (labfreed.org) is an open, vendor-neutral community initiative for pragmatic lab
digitalization -- simple, implementable building blocks instead of heavy
digital-transformation projects. This skill is about *using* the Python reference
implementation (PyPI package `labfreed`) to write code against it; it is not about
developing the library itself.

## The building blocks

| Building block | Purpose |
|---|---|
| **PAC-ID** | Minimal base identifier standing in for the many redundant IDs labs create for the same object (devices, substances, consumables, results, methods, calibrations...) |
| **PAC-CAT** | Optional layer on PAC-ID: standardized category/segment structure so identifiers are meaningful and interpretable across systems |
| **T-REX** | Human- and barcode-friendly data serialization -- lets data (quantities, dates, tables, booleans, text) travel attached to the PAC-ID itself, e.g. inside a QR code |
| **PAC-ID Resolver** | Resolves a scanned/typed PAC-ID to links/information about the object |
| **PAC-ID Attributes** | Lightweight metadata mechanism for an item (e.g. a display name, an image) |

A PAC-ID is always valid on its own; PAC-CAT, T-REX, and Attributes are optional layers on
top. For anatomy/grammar detail see `references/concepts.md`.

## Installing

```bash
pip install labfreed
```

Extra, less-stable pieces need extras: `pip install labfreed[extended]` (reference server/landing-page
code) or `pip install labfreed[experimental]` (unstable, no compatibility guarantees).

## Writing code against the package

See `references/quickstart.md` for copy-pasteable, verified examples of every core
operation: parsing/validating a PAC-ID, reading PAC-CAT categories, reading/creating
T-REX data, generating a QR code, using the PAC-ID Resolver, and serving/querying PAC-ID
Attributes.

## Canonical sources -- prefer these over memory if precision matters

- Explanations/intro: https://labfreed.org (see `/building-blocks/<name>/` for each block) -- readable overviews, not the normative spec text
- Python package: https://pypi.org/project/labfreed/ -- source at https://github.com/retothuerer/LabFREED (MIT license)
- Spec repos (source of truth for exact grammar/wording), each under github.com/ApiniLabs: PAC-ID, PAC-CAT, PAC-ID-Resolver, T-REX, PAC-Attributes

These move faster than this skill's cache of them -- re-check the live source for an exact
grammar rule, current version number, or a recent breaking change.

## Version note

The package went through breaking changes at v1.0.0 (module reorganization -- some import
paths changed; a PAC-CAT category rename; `Quantity.float` renamed to `Quantity.as_float`;
the PAC-ID Resolver's "coupling information table" terminology is being renamed to
"resolver configuration"). If you're looking at code, a tutorial, or an example written
against a pre-1.0 release, don't assume its imports or names still match current `main` --
check `references/quickstart.md` or the live repo instead of extrapolating from old code.
