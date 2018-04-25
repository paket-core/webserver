"""API Web server configuration."""
import os

import flasgger
import flask
import flask_limiter.util

import api.routes
import db
import paket
import logger

LOGGER = logger.logging.getLogger('pkt.api.server')
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


def init_sandbox(create_db=None, create_stellar=None, fund_stellar=None):
    """Initialize database with debug values and fund users. For debug only."""
    if create_db is None and bool(os.environ.get('PAKET_CREATE_DB')):
        create_db = True
    if create_stellar is None and bool(os.environ.get('PAKET_CREATE_STELLAR')):
        create_stellar = True
    if fund_stellar is None and bool(os.environ.get('PAKET_FUND_STELLAR')):
        fund_stellar = True

    if create_db:
        db.init_db()

    for paket_user, seed in [
            (key.split('PAKET_USER_', 1)[1], value)
            for key, value in os.environ.items()
            if key.startswith('PAKET_USER_')
    ]:
        if create_db:
            LOGGER.debug("Creating user %s", paket_user)
            keypair = paket.get_keypair(seed)
            pubkey, seed = keypair.address().decode(), keypair.seed().decode()
            try:
                db.create_user(pubkey, paket_user, seed)
                db.update_user_details(pubkey, paket_user, '123-456')
            except db.DuplicateUser:
                LOGGER.debug("User %s already exists", paket_user)
        if create_stellar:
            LOGGER.debug("Creating account %s", pubkey)  # TODO pubkey may be undefined
            try:
                paket.new_account(pubkey)
            except paket.StellarTransactionFailed:
                LOGGER.warning("address %s already exists", pubkey)
            paket.trust(keypair)  # TODO keypair may be undefined
        if fund_stellar:
            if pubkey == paket.ISSUER.address().decode():
                continue
            try:
                balance = paket.get_bul_account(pubkey)['balance']
            except paket.stellar_base.utils.AccountNotExistError:
                LOGGER.error("address %s does not exist", pubkey)
                continue
            if balance < 100:
                LOGGER.warning("user %s has only %s BUL", paket_user, balance)
                paket.send_buls(paket.ISSUER.address().decode(), pubkey, 1000 - balance)
