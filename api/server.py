"""API Web server configuration."""
import os

import flasgger
import flask
import flask_limiter.util

import api.routes
import db
import paket
import logger

LOGGER = logger.logging.getLogger('pkt.web')
logger.setup()

# Initialize flask app.
APP = flask.Flask('PaKeT')
APP.config['SECRET_KEY'] = os.environ.get('PAKET_SESSIONS_KEY', os.urandom(24))
STATIC_DIRS = ['static']
DEFAULT_LIMIT = os.environ.get('PAKET_SERVER_LIMIT', '100 per minute')
LIMITER = flask_limiter.Limiter(APP, key_func=flask_limiter.util.get_remote_address, default_limits=[DEFAULT_LIMIT])
APP.config['SWAGGER'] = api.routes.SWAGGER_CONFIG
flasgger.Swagger(APP)
APP.register_blueprint(api.routes.BLUEPRINT)


@APP.route('/')
@APP.route('/<path:path>', methods=['GET', 'POST'])
def catch_all_handler(path='index.html'):
    """All undefined endpoints try to serve from the static directories."""
    for directory in STATIC_DIRS:
        if os.path.isfile(os.path.join(directory, path)):
            return flask.send_from_directory(directory, path)
    return flask.jsonify({'status': 403, 'error': "Forbidden path: {}".format(path)}), 403


@APP.errorhandler(429)
def ratelimit_handler(error):
    """Custom error for rate limiter."""
    msg = 'Rate limit exceeded. Allowed rate: {}'.format(error.description)
    LOGGER.info(msg)
    return flask.make_response(flask.jsonify({'code': 429, 'error': msg}), 429)


def init_sandbox(fund=None):
    """Initialize database with debug values and fund users. For debug only."""
    db.init_db()

    for paket_user, seed in [
            (key.split('PAKET_USER_', 1)[1], value)
            for key, value in os.environ.items()
            if key.startswith('PAKET_USER_')
    ]:
        try:
            LOGGER.debug("Creating user %s", paket_user)
            keypair = paket.get_keypair(seed)
            pubkey, seed = keypair.address().decode(), keypair.seed().decode()
            db.create_user(pubkey, paket_user, seed)
            db.update_user_details(pubkey, paket_user, '123-456')
            LOGGER.debug("Created user %s", paket_user)
        except db.DuplicateUser:
            LOGGER.debug("User %s already exists", paket_user)
            continue
        if not fund:
            continue
        try:
            paket.new_account(pubkey)
            paket.trust(keypair)
            balance = paket.get_bul_account(pubkey)['balance']
            if balance and balance < 100:
                LOGGER.warning("user %s has only %s BUL", paket_user, balance)
                paket.send_buls(paket.ISSUER.address().decode(), pubkey, 1000 - balance)
        except paket.stellar_base.utils.AccountNotExistError:
            LOGGER.error("address %s does not exist", pubkey)
        except paket.StellarTransactionFailed:
            LOGGER.warning("address %s already exists", pubkey)
