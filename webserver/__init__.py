"""PAKET Web Server."""
import datetime
import os

import flasgger
import flask
import flask_cors
import flask_limiter.util

import util.logger

import webserver.validation

LOGGER = util.logger.logging.getLogger('pkt.web')
APP = flask.Flask('PaKeT')
flask_cors.CORS(APP)
APP.config['SECRET_KEY'] = os.environ.get('PAKET_SESSIONS_KEY', os.urandom(24))
STATIC_DIRS = ['static']
DEFAULT_LIMIT = os.environ.get('PAKET_SERVER_LIMIT', '100 per minute')
LIMITER = flask_limiter.Limiter(APP, key_func=flask_limiter.util.get_remote_address, default_limits=[DEFAULT_LIMIT])


class PaketJSONEncoder(flask.json.JSONEncoder):
    """Custom JSON encoder."""

    # pylint: disable=method-hidden
    def default(self, o):
        """Serialize time in ISO 8601 format."""
        if isinstance(o, datetime.datetime):
            return int(o.timestamp())
        return flask.json.JSONEncoder.default(self, o)
    # pylint: enable=wildcard-import


APP.json_encoder = PaketJSONEncoder


def setup(blueprint=None, swagger_config=None):
    """Register blueprint, flasgger, and catchall."""
    if blueprint:
        APP.register_blueprint(blueprint)
    if swagger_config:
        APP.config['SWAGGER'] = swagger_config
        flasgger.Swagger(APP)

    @APP.route('/')
    @APP.route('/<path:path>', methods=['GET', 'POST'])
    # pylint: disable=unused-variable
    def catch_all_handler(path='index.html'):
        """All undefined endpoints try to serve from the static directories."""
        for directory in STATIC_DIRS:
            if os.path.isfile(os.path.join(directory, path)):
                return flask.send_from_directory(directory, path)
        return flask.jsonify({'status': 403, 'error': "Forbidden path: {}".format(path)}), 403

    return APP


@APP.errorhandler(429)
def ratelimit_handler(error):
    """Custom error for rate limiter."""
    msg = 'Rate limit exceeded. Allowed rate: {}'.format(error.description)
    LOGGER.info(msg)
    return flask.make_response(flask.jsonify({'code': 429, 'error': msg}), 429)
