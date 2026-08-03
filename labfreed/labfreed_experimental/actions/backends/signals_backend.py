"""Signals Notebook ActionBackend - the reference/example well-known-actions backend."""
from collections.abc import Callable
import time

from labfreed.labfreed_experimental.actions.backend import (
    ContainerIsEmptyResult,
    UpdateAmountResult,
    UpdateLocationResult,
)
from labfreed.utilities.quantity import Quantity

# Delays (seconds) between retries of the AVAILABLE-status container lookup - measured
# against a real tenant (wega-int, 2026-07-31): after a restore_container()/
# update_container_attributes()/set_container_amount() write, /entities/search (what
# find_container_id_by_field() queries) took up to ~1.8s to reflect the container's new
# status. Without this, update_location()/update_amount() called right after a
# reset_attributes=True write to the same container - e.g. instrument_demo's
# accept_set_line_candidate() re-assigning a just-emptied/disposed bottle - can
# spuriously report "no AVAILABLE container found" even though the write already
# succeeded. Total wait (3.5s across 3 retries) is ~2x that measured lag.
_AVAILABLE_LOOKUP_RETRY_DELAYS_S = (0.5, 1.0, 2.0)

# UCUM is case-sensitive: "ML" is megalitre (mega- prefix + litre), not milliliter -
# deliberately not included here as a synonym for "mL". See developer-docs/TODO.md,
# "Real UCUM unit conversion for SignalsActionBackend.update_amount", for why this
# stays a small hardcoded whitelist instead of general unit conversion.
_VOLUME_UNITS_TO_ML = {
    'mL': 1.0,
    'L': 1000.0,
    'l': 1000.0,
    'uL': 0.001,
}


class SignalsActionBackend:
    """Implements ActionBackend on top of a SignalsInventoryClient.

    `location_pac_ids` maps a location PAC-ID to the Signals location id it stands
    for (tenant-specific, supplied by the caller - not hardcoded here).

    `create_container_attributes`, if given, is called with a PAC-ID that no AVAILABLE
    container was found for and must return the `attributes` dict to create one with
    (already containing that PAC-ID in whatever field/shape the tenant needs - typeId,
    contents, and the PAC-ID field's id are all tenant-specific, so this class stays
    agnostic to them and leaves building that dict entirely to the caller). Leave it
    None (default) to keep update_location()/update_amount() erroring on a missing
    container instead of creating one.

    `reset_container_attributes`, if given, is a *separate* factory called instead when
    `reset_attributes=True` is passed to either method and a container was found rather
    than created - deliberately not the same factory as create_container_attributes,
    because create goes through POST (which can set everything, e.g. typeId/contents)
    while reset goes through PATCH (which - confirmed against a real Signals tenant - 4xxs
    on typeId/contents/description: "Object instance has properties which are not allowed
    by the schema"). Whatever is and isn't PATCH-able is tenant/schema-specific, so this
    class doesn't guess at a subset - it's up to the caller to supply a factory that
    returns only what its tenant's PATCH endpoint actually accepts. Leave it None
    (default) to make `reset_attributes=True` a no-op.
    """

    def __init__(self, client, pac_id_field_name: str, location_pac_ids: dict[str, str],
                 create_container_attributes: Callable[[str], dict] | None = None,
                 reset_container_attributes: Callable[[str], dict] | None = None):
        self._client = client
        self._pac_id_field_name = pac_id_field_name
        self._location_pac_ids = location_pac_ids
        self._location_ids_to_pac_ids = {v: k for k, v in location_pac_ids.items()}
        self._create_container_attributes = create_container_attributes
        self._reset_container_attributes = reset_container_attributes

    def _find_container_id(self, pac_id: str) -> str | None:
        """Retries on a miss (see _AVAILABLE_LOOKUP_RETRY_DELAYS_S) - a genuinely-missing
        PAC-ID pays the full retry latency before this returns None, same as it always
        has, just slower."""
        container_id = self._client.find_container_id_by_field(self._pac_id_field_name, pac_id, status='AVAILABLE')
        for delay in _AVAILABLE_LOOKUP_RETRY_DELAYS_S:
            if container_id is not None:
                break
            time.sleep(delay)
            container_id = self._client.find_container_id_by_field(self._pac_id_field_name, pac_id, status='AVAILABLE')
        return container_id

    def _find_or_create_container_id(self, pac_id: str, *, reset_attributes: bool = False) -> str | None:
        """Same as _find_container_id(), except it creates a container (via
        create_container_attributes(pac_id)) when none exists yet and a factory was
        configured. Never creates a duplicate for a pac_id that already has a container
        in some other status (e.g. DISPOSED) - checked via a second, status-less lookup,
        same as create_test_container()'s existence check in labfreed-webtools' smoke
        test. Returns None, same as a plain not-found, in both the "truly nothing" and
        "exists but not AVAILABLE" cases - either way there's no AVAILABLE container to
        act on, and the latter must not silently spawn a duplicate.

        `reset_attributes=True` applies reset_container_attributes(pac_id) (not
        create_container_attributes - see the class docstring for why they're separate)
        to an already-found container too - useful for a demo where re-scanning a known
        PAC-ID should reset that container back to a pristine state instead of only
        touching it when it's missing. No-op (silently) if no reset factory is
        configured, same as the create-on-missing path."""
        container_id = self._find_container_id(pac_id)
        if container_id is not None:
            if reset_attributes and self._reset_container_attributes is not None:
                self._client.update_container_attributes(container_id, self._reset_container_attributes(pac_id))
            return container_id
        if self._create_container_attributes is None:
            return None
        if self._client.find_container_id_by_field(self._pac_id_field_name, pac_id) is not None:
            return None
        created = self._client.create_container(self._create_container_attributes(pac_id))
        created_id = created['id']
        return created_id.split(':')[1] if ':' in created_id else created_id

    def update_location(self, pac_id: str, location_pac_id: str, *, reset_attributes: bool = False) -> UpdateLocationResult:
        location_id = self._location_pac_ids.get(location_pac_id)
        if location_id is None:
            return UpdateLocationResult(ok=False, error=f'Unknown location PAC-ID {location_pac_id!r}.')

        container_id = self._find_or_create_container_id(pac_id, reset_attributes=reset_attributes)
        if container_id is None:
            return UpdateLocationResult(ok=False, error=f'No AVAILABLE container found for PAC-ID {pac_id!r}.')

        container = self._client.get_container(container_id)
        previous_location_id = container.get('attributes', {}).get('location', {}).get('id')
        previous_location_pac_id = self._location_ids_to_pac_ids.get(previous_location_id)

        self._client.set_container_location(container_id, location_id)
        location_name = self._client.get_location(location_id).get('attributes', {}).get('name')

        return UpdateLocationResult(ok=True, previous_location_pac_id=previous_location_pac_id, location_name=location_name)

    def update_amount(self, pac_id: str, quantity: str, *, reset_attributes: bool = False) -> UpdateAmountResult:
        try:
            q = Quantity.from_str_with_unit(quantity)
        except ValueError as e:
            return UpdateAmountResult(ok=False, error=str(e))
        if q is None:
            return UpdateAmountResult(ok=False, error=f'{quantity!r} is not a valid quantity string (expected e.g. "250 mL").')

        factor = _VOLUME_UNITS_TO_ML.get(q.unit)
        if factor is None:
            return UpdateAmountResult(ok=False, error=f'Unit {q.unit!r} is not a supported volume unit yet (only mL/L/uL).')

        value_mL = q.value * factor
        if value_mL <= 0:
            return UpdateAmountResult(ok=False, error='Amount must be greater than zero - use container_is_empty for an empty container.')

        container_id = self._find_or_create_container_id(pac_id, reset_attributes=reset_attributes)
        if container_id is None:
            return UpdateAmountResult(ok=False, error=f'No AVAILABLE container found for PAC-ID {pac_id!r}.')

        self._client.set_container_amount(container_id, value_mL)
        display_amount = self._client.get_container(container_id).get('attributes', {}).get('displayAmount')

        return UpdateAmountResult(ok=True, display_amount=display_amount)

    def container_is_empty(self, pac_id: str) -> ContainerIsEmptyResult:
        container_id = self._find_container_id(pac_id)
        if container_id is None:
            return ContainerIsEmptyResult(ok=False, error=f'No AVAILABLE container found for PAC-ID {pac_id!r}.')

        # Record the 0 mL amount before disposing - otherwise a disposed container keeps
        # displaying whatever non-zero amount was last set, which reads as inconsistent
        # with actually being empty. update_amount() can't be used for this itself (it
        # rejects value_mL <= 0 and points callers here instead), so this goes straight
        # through the client.
        self._client.set_container_amount(container_id, 0)
        self._client.dispose_container(container_id)
        return ContainerIsEmptyResult(ok=True, disposed=True)
