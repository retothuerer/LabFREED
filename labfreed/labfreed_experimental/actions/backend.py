"""The well-known action interface.

A fixed, small set of LabFREED-shaped actions - update-location, update-amount,
container-is-empty - that any backend (Signals Notebook, others later) can
implement, and that flask_layer.py dispatches HTTP requests to. Plain pydantic models
here (not LabFREED_BaseModel) since these are just request/response DTOs, not
CIT/PAC-ID-style objects that need the validation-message machinery.
"""
from typing import Protocol

from pydantic import BaseModel


class ActionResult(BaseModel):
    ok: bool
    error: str | None = None


class UpdateLocationResult(ActionResult):
    previous_location_pac_id: str | None = None
    location_name: str | None = None


class UpdateAmountResult(ActionResult):
    display_amount: str | None = None


class ContainerIsEmptyResult(ActionResult):
    disposed: bool = False


class ActionBackend(Protocol):
    """Implemented by a backend (e.g. SignalsActionBackend) to actually carry out
    the three well-known actions against whatever system it fronts.

    Scope, as of today: all three actions are substance-container inventory actions -
    every `pac_id` here identifies a container, and every method moves/consumes/disposes
    of it. A genuinely different action category (e.g. one whose subject PAC-ID is an
    instrument rather than a container - "start a run", "calibrate") would need its own
    Protocol and its own backend, not an extension of this one - don't add a
    non-container action here just because `actions` sounds generic."""

    def update_location(self, pac_id: str, location_pac_id: str) -> UpdateLocationResult: ...

    def update_amount(self, pac_id: str, quantity: str) -> UpdateAmountResult: ...

    def container_is_empty(self, pac_id: str) -> ContainerIsEmptyResult: ...
