# Setting up a PAC-ID Landing Page

When someone opens a PAC-ID in a plain browser instead of a LabFREED-aware app, they need somewhere to land: a page
that resolves the PAC-ID, shows whatever attributes are known about it, and links out to the services a
[PAC-ID Resolver](../../README.md#pac-id-resolver) config knows about (manuals, shop pages, calibration records, ...).

This folder is a complete, working example of such a landing page for the fictional issuer `METTORIUS.COM`. It's
built on `labfreed.labfreed_extended.pac_issuer_lib`, which wraps a Flask app around the same core
`labfreed.pac_attributes` classes used in the [PAC-ID Attributes](../../README.md#pac-id-attributes) example in the
main README — the landing page is really just "attribute server + resolver + templates" wired together for you.

Requires the `extended` extra (Flask, Flask-Cors, openpyxl):

```bash
pip install labfreed[extended]
```

## The pieces

### 1. Attribute data sources (`attribute_datasources.py`)

A plain Python module exposing two module-level names, `data_sources` and `translation_data_sources`, picked up via
`attribute_data_from_module(module, default_language)`. A few different kinds of data source are mixed together here:

- `Dict_DataSource` — attributes hard-coded as Python objects, keyed by PAC-ID (or, via `pac_to_key=...`, by
  something derived from it — e.g. `product_number_from_pac_url` so one entry covers every serial number of a
  `BAL500`).
- `DynamicDemoAttributeGroup` — attributes computed on the fly, restricted to matching PAC-IDs via a predicate
  (`is_BAL500`, `is_device`).

If you'd rather maintain attributes in a spreadsheet than in Python, `LocalExcelAttributeDataSource` (see
`examples/attribute_server/example_attributes_server.py`) reads them from a static `.xlsx` file instead — first
column is the lookup key, header row is the attribute keys. That's the "static files" option for a data source; it's
an alternative to `Dict_DataSource`, not something the attribute server requires.

Every attribute key used in a data source needs a translation, or `AttributeServerRequestHandler` warns at startup —
see `DictTranslationDataSource` calls throughout the file.

### 2. Resolver config (`resolver_configuration.with_macros.yaml`)

A normal [PAC-ID Resolver](../../README.md#pac-id-resolver) config, with `${MACRO}` placeholders substituted once at
first request:

```yaml
config:
- if: "True"
  entries:
  - service_name: Attributes
    service_type: attributes-generic
    application_intents: [attributes]
    template_url: "${BASE_URL}/attributes"   # <- points back at this app's own attribute server, below
- if: $.issuer == METTORIUS.COM AND $.categories[0].key == -MD
  entries:
  - service_name: Manual
    service_type: userhandover-generic
    application_intents: [document-manual]
    template_url: "${METTORIUS_HOME}/"
```

`${BASE_URL}` is filled in automatically with this app's own external URL; any other macro (`${METTORIUS_HOME}`
above) comes from the `resolver_macros` dict you pass to `create_app` (see below).

### 3. The app (`app.py`)

```python
app = IssuerFlaskAppFactory.create_app(
    issuer='METTORIUS.COM',
    site_meta=site_meta_data,                        # SiteMeta: title/description/author + nav bar links
    attribute_data=attribute_data,                    # from attribute_data_from_module(...) above
    path_to_custom_resources=path_to_custom_resources,# folder for your own static/ and templates/, see below
    pac_info_extender=MettoriusPacInfoExtender(),     # optional: attach your own fields to the resolved PacInfo
    resolver_macros=resolver_macros,
    use_issuer_resolver_config=False,
)
```

`create_app(...)` returns a plain `flask.Flask` instance with everything mounted:

| Route | What it does |
|---|---|
| `/<path>` | The landing page for PAC-ID `HTTPS://PAC.<issuer>/<path>` |
| `/resolver_config`, `/resolver_config.yaml` | The macro-substituted resolver config, as YAML |
| `/info_card` | A standalone PAC info-card fragment for `?pac_id=...` |
| `/attributes/...` | The embedded attribute server (only mounted if `attribute_data` was given) |
| `/static/...` | Static assets — see custom resources below |

### 4. Custom resources (branding)

`path_to_custom_resources` points at a folder; if it contains a `static/` or `templates/` subfolder, files there
override the library's bundled defaults (logo, CSS, page templates) by name — anything you don't override falls back
to the default. This example points it at its own directory (`Path(__file__).parent`) and overrides `static/logo.png`,
`static/styles_brand.css`, and a few product images.

### 5. Adding your own endpoints

`app` is just a Flask app, so you can register additional blueprints on it — see `bp_add_on` at the bottom of
`app.py` for a minimal example.

## Running it

There's no `if __name__ == '__main__':` block in `app.py` — run it like any Flask app:

```bash
flask --app examples.pac_mettorius_com.app run
```

or serve it with a WSGI server for anything beyond local dev, e.g. `gunicorn examples.pac_mettorius_com.app:app`.

## Just an attribute server, no landing page

If you only need to serve attributes (no landing page, resolver, or templates), skip
`IssuerFlaskAppFactory` and build the Flask app directly with `AttributeServerFactory.create_server_app(...)` —
see `examples/attribute_server/example_attributes_server.py` for a complete runnable example. It's the same
underlying `AttributeServerRequestHandler` as above, plus you're required to supply an `Authenticator` (that example
implements HTTP Basic Auth; pass `NoAuthRequiredAuthenticator()` to disable auth entirely).
