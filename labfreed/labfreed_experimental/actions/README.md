# Well-known actions

A fixed, small set of LabFREED-shaped actions - `update-location`, `update-amount`,
`container-is-empty` - that any backend (`SignalsActionBackend`, others later) can
implement (see `backend.py`'s `ActionBackend` Protocol), and that `flask_layer.py`
exposes as HTTP POST routes dispatching to that backend.

`resolver_config.yaml` is the one canonical CIT for these three actions
(`service_type: action-generic`) - a consuming app adds it via
`Labfreed_App_Infrastructure.add_resolver_config()`, substituting its own `${BASE_URL}`
(wherever `create_actions_blueprint()` ends up mounted). Once registered,
`process_pac()` surfaces the resolved actions on `PacInfo.actions`, queryable via
`pac_info.get_action_by_intent('update-location')` etc.

## Calling convention

An action's resolved URL only carries the CIT's usual PAC-ID-derived substitutions -
nothing else. Anything the action itself needs (the new location's PAC-ID, the UCUM
quantity) travels as a plain query parameter the caller appends on top of the resolved
URL, e.g. a resolved `.../actions/update_location` gets called as
`.../actions/update_location?pac_id=...&location=...`. See
`developer-docs/design-choices.md`, "Well-known action handler: `action-generic` params
travel as plain query params, not through the CIT template", for the full rationale -
this holds for *any* `action-generic` consumer of this package, not just Signals.

## Calling your own action endpoint from the same process

A Flask app that both hosts `flask_layer.py`'s blueprint *and* is itself the one
resolving/calling those actions (the common case: an app syncing its own inventory
through the well-known actions it also serves) should not make a real HTTP request back
into itself. Under a single- or few-worker WSGI deployment (e.g. Azure App Service's
default sync workers), a request handler that blocks waiting on an HTTP call back into
the same app can deadlock - there's no free worker left to serve that inbound call.

Instead, detect when the resolved action URL is this same app's own base URL and
dispatch in-process via Flask's/Werkzeug's own test client (`app.test_client()` /
`werkzeug.test.Client`), which drives the WSGI app directly through the Python call
stack - no socket, no separate worker - while still exercising the exact same Flask
dispatch (routing, blueprints, before/after-request hooks) a real HTTP call would. Fall
back to a real `requests.post()` for anything that resolves elsewhere.

This package doesn't ship this dispatch helper itself - it needs the consuming app's own
`Flask` instance and its own notion of "my base URL" - but any consumer wiring itself up
as an `action-generic` caller of its own actions should implement this same shape:

```python
from urllib.parse import urlsplit

import requests
from flask import current_app


def call_action(pac_info, intent: str, own_base_url: str, **params) -> dict:
    """Resolve `intent` (e.g. 'update-location') to a Service via `pac_info`, call it
    with `params` as the query string, and return the parsed JSON response body."""
    service = pac_info.get_action_by_intent(intent)
    if service is None:
        raise RuntimeError(f"No {intent!r} action is configured for {pac_info.pac_url}.")

    if urlsplit(service.url).netloc == urlsplit(own_base_url).netloc:
        resp = current_app.test_client().post(urlsplit(service.url).path, query_string=params)
        if resp.status_code >= 400:
            raise RuntimeError(f"{service.service_name} action failed: HTTP {resp.status_code}")
        return resp.get_json()

    resp = requests.post(service.url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()
```

See `labfreed-webtools`' `instrument_demo/action_client.py` for the concrete
implementation of this pattern, and `developer-docs/design-choices.md`, "Same-process
action calls dispatch in-process, not over real HTTP", for why it's shaped this way.
