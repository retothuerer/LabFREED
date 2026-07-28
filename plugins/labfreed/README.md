# labfreed (Claude Code plugin)

Gives Claude reference knowledge and copy-pasteable code examples for the
[`labfreed`](https://pypi.org/project/labfreed/) Python package -- the reference
implementation of [LabFREED](https://labfreed.org)'s building blocks: PAC-ID, PAC-CAT,
T-REX, PAC-ID Resolver, and PAC-ID Attributes.

Install it in any project where you (or Claude) will be writing code against `labfreed`,
and Claude will pick it up automatically whenever PAC-ID/PAC-CAT/T-REX/CIT/PAC-ID
Attributes come up -- no need to explain the ecosystem or paste in example code each time.

## Contents

- **Skill:** `labfreed` -- what the building blocks are, PAC-ID/PAC-CAT anatomy and
  grammar, and a quickstart reference with working code for every core operation (parse
  and validate a PAC-ID, read PAC-CAT categories, read/create T-REX data, generate a QR
  code, use the PAC-ID Resolver, serve/query PAC-ID Attributes).

This is a *usage* skill -- for developing the `labfreed` library itself, see the
project-local skills in the main repo's `.claude/skills/`.

## Installation

```
/plugin marketplace add retothuerer/LabFREED
/plugin install labfreed@labfreed-plugins
```
