# LabFREED concepts -- anatomy, rules, building blocks in detail

Point-in-time summary, distilled from the spec repos. Re-fetch the live pages/repos if
precision matters (an exact grammar rule, a version number) -- these move faster than
this file.

## PAC-ID
"Standardized Representation for Identifiers." https://labfreed.org/building-blocks/pac-id/

Intentionally minimal base spec: a single identifier that can replace the many redundant
identifiers labs create for the same object -- materials (devices, substances,
consumables) and data (results, methods, calibrations, progress). Any valid
PAC-CAT/T-REX/Attributes usage builds on top of a valid PAC-ID; a bare PAC-ID is still
valid without those layers.

**PAC-IDs are always upper case -- every character, including the scheme and domain**
(e.g. `HTTPS://PAC.METTORIUS.COM/-MD/BAL500/210263`, not `https://pac.mettorius.com/...`).
Confirmed directly by the T-REX spec text: *"PAC-IDs thus only use characters `0-9`,
`A-Z` (upper-case only) and `$*+-./,:`."* This applies to the PAC-ID itself -- it does
**not** extend to ordinary URLs referenced elsewhere (resolver service URLs, Attribute
`resource`/`reference` values pointing at non-PAC-ID assets) -- those stay normal
lower-case URLs per standard web convention.

### Anatomy

```
HTTPS://PAC.METTORIUS.COM/-MD/240:BAL500/21:210263
\____/ \_____________/ \____________________________/
scheme     issuer                  identifier
                        \___/ \___________/ \_________/
                     category   id segment   id segment
                        key        (key:value)   (key:value)
```

- **`issuer`** -- the party that issued the identifier, as a domain name prefixed `PAC.`
  (e.g. `PAC.METTORIUS.COM`). Should be registered to that party.
- **`identifier`** -- one or more `/`-separated **`id segment`**s. No `id segment` may be
  empty (a trailing or doubled `/` is invalid, not silently normalized away); max 256
  characters total.
- **`id segment`** -- a single path segment. Can optionally be an `id segment key`:`id
  segment value` pair (`:`-separated), e.g. `21:210263`. MUST NOT start with `-` unless
  it's a PAC-CAT category key.
- **`id segment key`** -- RECOMMENDED to be a well-known key (often a numeric GS1
  Application Identifier, e.g. `21` = Serial Number, `240` = Model/Product code).

### Extensions (`*`-separated, after the identifier)

`name$type/data`, `*`-delimited from the PAC-ID and from each other. Two conventional
first extensions: **Display Name** (`N$TEXT/...`) and **Summary** (`SUM$TREX/...`,
T-REX-formatted). Short notation omits `name`/`type` for these two specifically:

```
HTTPS://PAC.METTORIUS.COM/-DR/8956757*3SQHOW5NBOGUZDM4VWC9N3K99JT3WO0X28DAXDF/WEIGHT$GRM:2.05+TARE$GRM:100.01
```

### Derivation namespaces (aliquots, cross-issuer derivation)

An issuer MAY extend its own PAC-ID by appending segments (batch -> container, etc.). A
**different** party extending someone else's PAC-ID (e.g. a lab making an aliquot from a
manufacturer's container) MUST insert a **derivation namespace segment**,
`+<namespace>`, establishing a new namespace boundary for everything appended after it:

```
HTTPS://PAC.OMNIZYME.COM/-MS/240:AMYLASE/10:AB9876/21:9876/+ACMELABS.COM/250:1
```

Multiple `+<namespace>` segments MAY chain (multiple parties deriving in sequence).

## PAC-CAT
"Assign More Meaning to PAC-IDs With Standardized Structure."
https://labfreed.org/building-blocks/pac-cat/ -- spec repo:
https://github.com/ApiniLabs/PAC-CAT

Optional layer: `identifier` = a category-key segment (starts with `-` followed by
letters) followed by that category's segments, then optional custom segments.
Explicitly, "a PAC-ID can be valid, without following this specification."

**Category keys and their segments** (`*` = mandatory):

Materials (physical, uniquely identifiable things):
| Category | Key | Segments |
|---|---|---|
| Device (instrument, equipment) | `-MD` | `240` Model code *, `21` Serial number * |
| Substance (sample, aliquot, product) | `-MS` | `240` Product number *, `10` Batch, `20` Container size, `21` Container number, `250` Aliquot |
| Consumable | `-MC` | `240` Product code *, `10` Batch, `20` Packaging size, `21` Serial number, `250` Aliquot |
| Misc material (avoid) | `-MX` | same shape as above |

Data (recorded information -- each just needs a single ID):
| Category | Key | Segments |
|---|---|---|
| Result (completed run/report/CoA) | `-DR` | `21` ID * |
| Method (recipe/SOP/run config) | `-DM` | `21` ID * |
| Calibration | `-DC` | `21` ID * |
| Progress (live/in-flight data) | `-DP` | `21` ID * |
| Static (metadata/datasheet) | `-DS` | `21` ID * |
| Misc data (avoid) | `-DX` | `21` ID * |

Processors (systems that assign/manage materials or data):
| Category | Key | Segments |
|---|---|---|
| Software | `-PS` | `21` Processor instance *, `240` Processor code |
| Misc processor (avoid) | `-PX` | same shape |

Misc (generic fallback, avoid): `-X`, `21` ID *.

If an instrument incorporates software functionality, PAC-CAT recommends prioritizing the
*material* aspect (`-MD`), not `-PS`.

**Second category = issuing system.** A PAC-ID MAY concatenate a second category
identifying *what system generated/manages this record* -- the first category is always
what the PAC-ID actually refers to:

```
HTTPS://PAC.METTORIUS.COM/-DR/240:123ABC/8008:20230205/-MD/240:BAL500/21:210263
                        \_result, from a specific run__/\_the device that produced it__/
```

**Short notation** -- omit `id segment key`s; they're implicitly assigned by the
recommended segment order above, until an explicit key that differs is reached or a
`-`-prefixed segment starts:

```
HTTPS://PAC.METTORIUS.COM/-MD/BAL500/210263/8008:20230205
```

## T-REX
"Human- and Barcode-Friendly Data Serialization." https://labfreed.org/building-blocks/t-rex/

Lets data be attached directly to a PAC-ID, e.g. packed into a QR code alongside the
identifier itself. Supported value types: quantities, dates, tables, booleans, text.
Extensions (e.g. a base36-encoded "display name" extension) can ride along in the same
serialization.

## PAC-ID Resolver
"Seamless User Navigation Across System Borders." https://labfreed.org/building-blocks/pac-id-resolver/

Given a scanned/typed PAC-ID, resolves it to links/information about the identified
object, configurable per object type/category. The reference implementation supports
combining multiple resolver configs and doing service-URL discovery/reachability checks.

**Terminology in flux**: this building block's central mechanism used to be called the
**Coupling Information Table (CIT)** -- CIT v1 stable, CIT v2 draft. As of the package's
v1.0.0 release this is being renamed to "resolver configuration"; you may see both terms
(`load_cit`, `resolver_configs=...`) in the same codebase during the transition. Don't
assume one has fully replaced the other without checking current code/docs.

## PAC-ID Attributes
"Lightweight mechanism to provide metadata about an item."
https://labfreed.org/building-blocks/pac-id-attributes/

Balances simplicity, standardization, semantics, and display needs (e.g. surfacing a
product image) as metadata attached to a PAC-ID, without baking it into the identifier
itself.

## Example issuers -- reuse these, don't invent new ones

Confirmed from the actual spec repos (PAC-ID, PAC-CAT, T-REX, Resolver, Attributes
READMEs) -- use these by default when writing PAC-ID examples:

| Issuer | Role in the real spec examples |
|---|---|
| `METTORIUS.COM` | **The** canonical example instrument manufacturer -- used pervasively, especially for balances (`-MD/BAL500/...`). Default choice for any instrument/device example. |
| `ACME.COM` | Example laboratory/company as a generic asset owner. |
| `ACMELABS.COM` | Example laboratory that *derives* from someone else's PAC-ID -- the "downstream lab" role, as opposed to `ACME.COM`'s "asset owner" role. |
| `OMNIZYME.COM` | Example substance/material manufacturer (an aliquotable enzyme product, `-MS`). |
| `PARTNERLAB.ORG` | Example partner lab in a chained multi-party derivation. |
| `EOSTEC.COM` | Example software/SaaS vendor (`-PS`). |

## No published spec version numbers

labfreed.org itself does not publish explicit spec version numbers for these building
blocks. Versioning shows up instead in the reference implementation (PyPI package
version) and in the CIT v1/v2 (resolver-config) distinction. Don't invent a spec version
number if asked -- say it isn't published, and point to the repo/package version instead.
