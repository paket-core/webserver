"""PaKeT Web Server."""
import os

import flasgger
import flask
import flask_limiter.util

try:
    import logger
    logger.setup()
    LOGGER = logger.logging
except ModuleNotFoundError:
    import logging
    LOGGER = logging
LOGGER = LOGGER.getLogger('pkt.web')


# Initialize flask app.
APP = flask.Flask('PaKeT')
APP.config['SECRET_KEY'] = os.environ.get('PAKET_SESSIONS_KEY', os.urandom(24))
STATIC_DIRS = ['static']
DEFAULT_LIMIT = os.environ.get('PAKET_SERVER_LIMIT', '100 per minute')
LIMITER = flask_limiter.Limiter(APP, key_func=flask_limiter.util.get_remote_address, default_limits=[DEFAULT_LIMIT])


def run(blueprint=None, swagger_config=None, debug=None):
    """Register blueprint, initialize flasgger, register catchall, and run."""
    if blueprint:
        APP.register_blueprint(blueprint)
    if swagger_config:
        APP.config['SWAGGER'] = swagger_config
        flasgger.Swagger(APP)


    @APP.route('/')
    @APP.route('/<path:path>', methods=['GET', 'POST'])
    def catch_all_handler(path='index.html'):
        """All undefined endpoints try to serve from the static directories."""
        for directory in STATIC_DIRS:
            if os.path.isfile(os.path.join(directory, path)):
                return flask.send_from_directory(directory, path)
        return flask.jsonify({'status': 403, 'error': "Forbidden path: {}".format(path)}), 403


    APP.run('0.0.0.0', 5000, debug)


@APP.errorhandler(429)
def ratelimit_handler(error):
    """Custom error for rate limiter."""
    msg = 'Rate limit exceeded. Allowed rate: {}'.format(error.description)
    LOGGER.info(msg)
    return flask.make_response(flask.jsonify({'code': 429, 'error': msg}), 429)
