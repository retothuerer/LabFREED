"""Flask HTTP layer for the well-known actions (backend.py)."""
try:
    from flask import Blueprint, jsonify, request
except ImportError:
    raise ImportError("Please install labfreed with the [experimental] extra: pip install labfreed[experimental]")

from labfreed.labfreed_experimental.actions.backend import ActionBackend


def create_actions_blueprint(backend: ActionBackend, url_prefix: str = '/actions') -> Blueprint:
    """Build a Blueprint exposing the three well-known actions as POST routes
    (`/update_location`, `/update_amount`, `/container_is_empty`), each reading its
    parameters from the query string and dispatching to `backend`.

    Every response is a 200 with the action's result JSON (`ok`/`error`, plus whatever
    else that action reports) - success/failure of the action itself lives in that
    body, not the HTTP status. A 400 is reserved for a request missing a parameter the
    route needs to even call the backend.
    """
    bp = Blueprint('labfreed_actions', __name__, url_prefix=url_prefix)

    def _required_arg(name):
        value = request.args.get(name)
        if not value:
            return None, (jsonify({'ok': False, 'error': f'Missing required parameter {name!r}.'}), 400)
        return value, None

    @bp.route('/update_location', methods=['POST'])
    def update_location():
        pac_id, error = _required_arg('pac_id')
        if error:
            return error
        location_pac_id, error = _required_arg('location')
        if error:
            return error
        result = backend.update_location(pac_id, location_pac_id)
        return jsonify(result.model_dump())

    @bp.route('/update_amount', methods=['POST'])
    def update_amount():
        pac_id, error = _required_arg('pac_id')
        if error:
            return error
        amount, error = _required_arg('amount')
        if error:
            return error
        result = backend.update_amount(pac_id, amount)
        return jsonify(result.model_dump())

    @bp.route('/container_is_empty', methods=['POST'])
    def container_is_empty():
        pac_id, error = _required_arg('pac_id')
        if error:
            return error
        result = backend.container_is_empty(pac_id)
        return jsonify(result.model_dump())

    return bp
