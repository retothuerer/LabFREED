"""Bare-metal Signals Notebook REST client.

Thin wrapper around the Inventory / Entities REST API. Knows nothing about PAC-IDs,
well-known actions, or any backend-specific concept - every method is parameterized
generically, so this can be reused by anything that needs to talk to Signals Notebook
inventory. Domain-specific translation (PAC-ID <-> Signals concepts) lives in
signals_backend.py instead.

Moved here from labfreed-webtools' instrument_demo/signals_client.py, which was
confirmed working against a real tenant (wega-int, 2026-07-30) - see that project's
request_data_query.json/request_data_post_inventory.json for the confirmed request
shapes this was built against, and create_container()'s docstring for one example of
where inventory.yaml's documented schema doesn't quite match a real tenant's behavior.

`base_url`/`api_key` are required constructor args, not read from the environment here
- unlike the labfreed-webtools module this was moved from, a library module shouldn't
reach into os.environ/.env on its own (its old implicit `load_dotenv()` walked up from
*this file's* directory looking for a .env, which broke the moment this file moved out
of the consuming app's own directory tree). The caller (already doing its own env/config
loading) passes these in explicitly.
"""
import logging

import requests


def _uuid_from_eid(eid: str) -> str:
    """'container:<uuid>:ivt' -> '<uuid>' - the id form /inventory/containers/{containerId} takes."""
    parts = eid.split(':')
    return parts[1] if len(parts) >= 2 else eid


class SignalsInventoryClient:
    """Thin wrapper around the Signals Notebook Inventory / Entities REST API."""

    def __init__(self, base_url: str, api_key: str, http_client=None):
        base_url = base_url.rstrip('/')
        if not base_url.endswith('/api/rest/v1.0'):
            base_url += '/api/rest/v1.0'
        self._base_url = base_url
        self._session = http_client or requests.Session()
        self._session.headers['x-api-key'] = api_key
        # Signals Notebook is a JSON:API - it 415s plain "application/json" (what
        # requests' json= kwarg sends by default).
        self._session.headers['Content-Type'] = 'application/vnd.api+json'
        self._session.headers['Accept'] = 'application/vnd.api+json'

    #: Terminal statuses a disposed container never leaves - see
    #: find_container_id_by_field's docstring on why these stick around in the search
    #: index forever. list_containers(active_only=True) excludes both.
    _INACTIVE_STATUSES = ('DISPOSED', 'FINAL_DISPOSED')

    def list_containers(self, active_only: bool = False) -> list[dict]:
        """Page through /entities/search (source=IVT) for every inventory container.

        Returns EntityIndexData entries (id/eid/name/...) - a listing/overview helper.

        `active_only=True` excludes DISPOSED/FINAL_DISPOSED containers, so callers don't
        each need to know which statuses count as "gone" - that knowledge lives here.
        """
        query_clauses = [{"$match": {"field": "type", "value": "container", "mode": "keyword"}}]
        if active_only:
            query_clauses += [
                {"$not": [{"$match": {"field": "fields.Status", "in": "tags", "value": status, "mode": "keyword"}}]}
                for status in self._INACTIVE_STATUSES
            ]
        query = {"$and": query_clauses} if len(query_clauses) > 1 else query_clauses[0]

        containers = []
        offset = 0
        limit = 100
        total = None
        while total is None or offset < total:
            resp = self._session.post(
                f'{self._base_url}/entities/search',
                params={'source': 'IVT', 'page[offset]': offset, 'page[limit]': limit},
                json={"query": query},
            )
            resp.raise_for_status()
            page = resp.json()
            data = page.get('data', [])
            containers.extend(data)
            total = page.get('meta', {}).get('total', len(containers))
            offset += limit
            if not data:
                break
        return containers

    def find_container_id_by_field(self, field_name: str, value: str, status: str | None = None) -> str | None:
        """Find a container whose custom `field_name` field equals `value`, via one
        /entities/search query (source=IVT, type=container, tag-matched on
        "container.<field_name>"). Confirmed working against a real tenant (wega-int,
        2026-07-30): custom inventory container fields are indexed under
        "container.<Field Title>" (exact title, case-sensitive) in the "tags" facet -
        built-ins use "fields."/"system." instead. See request_data_query.json (in
        labfreed-webtools' instrument_demo/) for the confirmed request shape.

        `status` (indexed as "fields.Status", e.g. "AVAILABLE") restricts the match to
        that status - pass it when a disposed container isn't a usable answer (e.g.
        finding one to move/refill: a disposed container stays in the search index
        forever, so without this a field value that's ever been reused, like a fixed test
        PAC-ID, can match a stale disposed container instead of, or ahead of, the live
        one). Leave it None for an existence check across any status.
        """
        query_clauses = [
            {"$match": {"field": "type", "value": "container", "mode": "keyword"}},
            {"$match": {"field": f"container.{field_name}", "in": "tags", "value": value, "mode": "keyword"}},
        ]
        if status is not None:
            query_clauses.append({"$match": {"field": "fields.Status", "in": "tags", "value": status, "mode": "keyword"}})
        resp = self._session.post(
            f'{self._base_url}/entities/search',
            params={'page[offset]': 0, 'page[limit]': 20, 'source': 'IVT'},
            json={
                "query": {
                    "$and": query_clauses
                }
            },
        )
        resp.raise_for_status()
        containers = resp.json().get('data', [])
        if not containers:
            return None
        if len(containers) > 1:
            logging.warning(f'Multiple containers matched {field_name}={value!r}; using the first one')
        return _uuid_from_eid(containers[0]['id'])

    def get_container(self, container_id: str) -> dict:
        """GET /inventory/containers/{containerId}."""
        resp = self._session.get(f'{self._base_url}/inventory/containers/{container_id}')
        resp.raise_for_status()
        return resp.json()['data']

    def get_location(self, location_id: str) -> dict:
        """GET /inventory/locations/{locationId}. Unlike the container endpoints above,
        not yet confirmed against a real tenant - only used so far for the well-known
        actions' update_location result to report a human-readable location name."""
        resp = self._session.get(f'{self._base_url}/inventory/locations/{location_id}')
        resp.raise_for_status()
        return resp.json()['data']

    def create_container(self, attributes: dict) -> dict:
        """POST /inventory/containers. `attributes` is the JSON:API `data.attributes` object
        (typeId, description, location, contents, fields, ...) - see inventory.yaml's
        ContainerAttributes schema and request_data_post_inventory.json (in
        labfreed-webtools' instrument_demo/) for the confirmed request shape. `contents`
        is required in practice by this tenant's container types even though
        inventory.yaml doesn't mark it required - omitting it 4xxs with "Missed required
        field contents.".

        Returns the created container (ExtIvtContainer). Confirmed against a real tenant
        (wega-int, 2026-07-30): unlike GET, which returns `data` as a single object, this
        endpoint wraps it in a one-element array - hence the [0] below.
        """
        resp = self._session.post(
            f'{self._base_url}/inventory/containers',
            json={'data': {'type': 'inventoryContainer', 'attributes': attributes}},
        )
        resp.raise_for_status()
        return resp.json()['data'][0]

    def update_container_attributes(self, container_id: str, attributes: dict) -> None:
        """PATCH /inventory/containers/{containerId} with an arbitrary `attributes` dict -
        the general form set_container_location()/set_container_amount() are narrow,
        single-field wrappers around. `force=true` skips the optimistic-locking digest,
        same as those."""
        resp = self._session.patch(
            f'{self._base_url}/inventory/containers/{container_id}',
            params={'force': 'true'},
            json={"data": {"type": "inventoryContainer", "attributes": attributes}},
        )
        resp.raise_for_status()

    def set_container_location(self, container_id: str, location_id: str) -> None:
        """PATCH /inventory/containers/{containerId}. `force=true` skips the optimistic-locking digest."""
        resp = self._session.patch(
            f'{self._base_url}/inventory/containers/{container_id}',
            params={'force': 'true'},
            json={"data": {"type": "inventoryContainer", "attributes": {"location": {"id": location_id}}}},
        )
        resp.raise_for_status()

    def set_container_amount(self, container_id: str, value_mL: float) -> None:
        """PATCH /inventory/containers/{containerId}/amount. Sets the *absolute* remaining amount."""
        resp = self._session.patch(
            f'{self._base_url}/inventory/containers/{container_id}/amount',
            params={'force': 'true'},
            json={"data": {"type": "inventoryContainer", "attributes": {"amount": f'{value_mL} ml'}}},
        )
        resp.raise_for_status()

    def dispose_container(self, container_id: str) -> None:
        """POST /inventory/containers/{containerId}/status/dispose.

        Reversible - use the 'finalDispose' action instead if the removal must be permanent
        (it also blocks any further location/amount changes on that container). See
        restore_container() to undo this.
        """
        resp = self._session.post(
            f'{self._base_url}/inventory/containers/{container_id}/status/dispose',
            params={'force': 'true'},
        )
        resp.raise_for_status()

    def restore_container(self, container_id: str) -> None:
        """POST /inventory/containers/{containerId}/status/restore. Undoes dispose_container()
        - brings a DISPOSED container back to AVAILABLE so it can be moved/refilled again.
        Only valid from DISPOSED; a FINAL_DISPOSED container cannot be restored.
        """
        resp = self._session.post(
            f'{self._base_url}/inventory/containers/{container_id}/status/restore',
            params={'force': 'true'},
        )
        resp.raise_for_status()
