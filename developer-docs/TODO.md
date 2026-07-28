# TODO

General backlog of things worth picking up later - not scoped to any one topic. Ideas
that relate to an entry in [`design-choices.md`](design-choices.md) should cross-link
to it (both directions), but this file isn't exclusively for design-choice follow-ups -
anything worth not losing track of belongs here.

---

## Use `ValidationInfo.context` to replace the manual nested-message tree-walk

Related to: ["Non-fatal, severity-tiered validation instead of plain pydantic
errors"](design-choices.md#non-fatal-severity-tiered-validation-instead-of-plain-pydantic-errors)

Idea: instead of `self._validation_messages` (a `PrivateAttr` on every
`LabFREED_BaseModel` instance) plus `_get_nested_validation_messages()` walking the
object graph afterward, validators could append to a shared `context['messages']`
list/dict passed into `Model.model_validate(data, context={...})`. Confirmed
empirically (pydantic 2.13.4) that pydantic threads the *same* context object down into
nested models' validators automatically within one `model_validate()` call - no manual
recursion needed, and it survives even if validation later raises, since the caller
still holds a reference to that mutable object.

Blocker: this only works when construction goes through `model_validate()` /
`model_validate_json()`. A plain `Model(...)` call never receives it - confirmed
`info.context` is `None` even when passing `context=` as a kwarg to `__init__` (silently
treated as an unrecognized field under default `extra='ignore'`, no error raised).
Before attempting this, audit whether `LabFREED_BaseModel` subclasses are ever
constructed via plain `Model(...)` instead of `.model_validate(...)` anywhere in the
codebase - including by consumers of the package, not just internally. If so, this
would silently drop messages with no error, which is worse than the current recursive
walk it would replace.
