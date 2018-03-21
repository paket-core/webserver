"""Web JSON swagger API to PaKeT smart contract."""
import functools
import os

import flasgger
import flask
import flask_limiter.util

import db
import paket
import logger

VERSION = '1'
LOGGER = logger.logging.getLogger('pkt.api')
logger.setup()

# Initialize flask app.
APP = flask.Flask('PaKeT')
APP.config['SECRET_KEY'] = os.environ.get('PAKET_SESSIONS_KEY', os.urandom(24))
STATIC_DIRS = ['static']
DEFAULT_LIMIT = os.environ.get('PAKET_SERVER_LIMIT', '100 per minute')
LIMITER = flask_limiter.Limiter(APP, key_func=flask_limiter.util.get_remote_address, default_limits=[DEFAULT_LIMIT])
APP.config['SWAGGER'] = {
    'title': 'PaKeT API',
    'uiversion': 3,
    'specs_route': '/',
    'info': {
        'description': 'Web API Server for The PaKeT Project',
        'contact': {
            'name': 'Israel Levin',
            'email': 'Israel@paket.global',
            'url': 'www.paket.global',
        },
        'version': VERSION,
        'license': {
            'name': 'Apache 2.0',
            'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'
        },
    },
    'specs': [{
        'endpoint': '/',
        'route': '/apispec.json',
        'rule_filter': lambda rule: True,  # all in
        'model_filter': lambda tag: True,  # all in
    }],
}
flasgger.Swagger(APP)


class MissingFields(Exception):
    """Missing field in args."""


class InvalidField(Exception):
    """Invalid field."""


class FootprintMismatch(Exception):
    """Invalid address field."""


class InvalidSignature(Exception):
    """Invalid address field."""


def check_missing_fields(fields, required_fields):
    """Raise exception if there are missing fields."""
    if required_fields is None:
        required_fields = set()
    missing_fields = set(required_fields) - set(fields)
    if missing_fields:
        raise MissingFields(', '.join(missing_fields))


def check_and_fix_values(kwargs):
    """
    Raise exception for invalid values.
    "_buls" and "_timestamp" fields must be valid integers.
    "_address" fields must be valid addresses.
    """
    for key, value in kwargs.items():
        if key.endswith('_buls') or key.endswith('_timestamp'):
            try:
                # Cast to str before casting to int to make sure floats fail.
                int_val = int(str(value))
            except ValueError:
                raise InvalidField("the value of {}({}) is not an integer".format(key, value))
            if int_val < 0:
                raise InvalidField("the value of {}({}) is less than zero".format(key, value))
            kwargs[key] = int_val
        elif key.endswith('_address'):
            # For debug purposes, we allow user IDs as addresses.
            LOGGER.warning("Attempting conversion of user ID %s to address", value)
            kwargs[key] = get_user_address(value)
            if not paket.W3.isAddress(kwargs[key]):
                raise InvalidField("value of {} is not a valid address".format(key))
    return kwargs


def check_footprint(footprint, url, kwargs):
    """
    Raise exception on invalid footprint.
    Currently does not do anything.
    """
    # Copy kwargs before we destroy it.
    kwargs = dict(kwargs)
    footprint = footprint.split(',')
    if url != footprint[0]:
        raise FootprintMismatch("footprint {} does not match call to {}".format(footprint[0], url))
    try:
        db.update_nonce(kwargs.pop('user_address'), footprint[-1])
    except db.InvalidNonce as exception:
        raise FootprintMismatch(str(exception))
    for key, val in [keyval.split('=') for keyval in footprint[1:-1]]:
        try:
            call_val = str(kwargs.pop(key))
        except KeyError:
            raise FootprintMismatch("footprint has extra value {} = {}".format(key, val))
        if call_val != val:
            raise FootprintMismatch("footprint {} = {} does not match call {} = {}".format(key, val, key, call_val))
    if kwargs:
        raise FootprintMismatch("footprint is missing a value for {}".format(', '.join((kwargs.keys()))))
    return footprint


def get_user_address(paket_user):
    """
    Get a user's address from paket_user (for debug only). Create a user if none is found.
    Will eventually merge into check_signature.
    """
    try:
        user_address = db.get_user_address(paket_user)
    except db.UnknownUser:
        user_address = paket.new_account()
        db.create_user(user_address)
        db.update_user_details(user_address, None, None, paket_user)
    return user_address


def check_signature(pubkey, footprint, signature):
    """
    Raise exception on invalid signature.
    Currently does not do anything.
    """
    pubkey = pubkey + signature
    LOGGER.warning("Not checking signature for %s", footprint)


def optional_arg_decorator(decorator):
    """A decorator for decorators than can accept optional arguments."""
    @functools.wraps(decorator)
    def wrapped_decorator(*args, **kwargs):
        """A wrapper to return a filled up function in case arguments are given."""
        if len(args) == 1 and not kwargs and callable(args[0]):
            return decorator(args[0])
        return lambda decoratee: decorator(decoratee, *args, **kwargs)
    return wrapped_decorator


# Since this is a decorator the handler argument will never be None, it is
# defined as such only to comply with python's syntactic sugar.
@optional_arg_decorator
def api_call(handler=None, required_fields=None):
    """
    A decorator to handle all API calls: extracts arguments, validates them,
    fixes them, handles authentication, and then passes them to the handler,
    dealing with exceptions and returning a valid response.
    """
    @functools.wraps(handler)
    def _api_call(*_, **kwargs):
        # pylint: disable=broad-except
        # If anything fails, we want to catch it here.
        response = {'status': 500, 'error': 'Internal server error'}
        try:
            kwargs = flask.request.values.to_dict()
            check_missing_fields(kwargs.keys(), required_fields)
            kwargs = check_and_fix_values(kwargs)
            kwargs['user_address'] = get_user_address(flask.request.headers.get('X-Pubkey'))
            footprint = check_footprint(flask.request.headers.get('X-Footprint'), flask.request.url, kwargs)
            check_signature(kwargs['user_address'], footprint, flask.request.headers.get('X-Signature'))
            response = handler(**kwargs)
        except MissingFields as exception:
            response = {'status': 400, 'error': "Request does not contain field(s): {}".format(exception)}
        except InvalidField as exception:
            response = {'status': 400, 'error': str(exception)}
        except FootprintMismatch as exception:
            response = {'status': 403, 'error': str(exception)}
        except db.DuplicateUser as exception:
            response = {'status': 409, 'error': str(exception)}
        except paket.NotEnoughFunds as exception:
            response = {'status': 402, 'error': str(exception)}
        except Exception as exception:
            LOGGER.exception("Unknown validation exception. Headers: %s", flask.request.headers)
            response['debug'] = str(exception)
        if 'error' in response:
            LOGGER.warning(response['error'])
        return flask.make_response(flask.jsonify(response), response.get('status', 200))
    return _api_call


@APP.route("/v{}/wallet_address".format(VERSION), methods=['POST'])
@api_call
def wallet_address_handler(user_address):
    """
    Get the address of the wallet. This address can be used to send BULs to.
    ---
    tags:
    - wallet
    parameters:
      - name: X-Pubkey
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/wallet_address,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
    responses:
      200:
        description: an address
        schema:
          properties:
            address:
              type: string
              format: string
              description: address of te BUL wallet
          example:
            {
                "status": 200,
                "address": "0xa5F478281ED1b94bD7411Eb2d30255F28b833e28"
            }
        """
    return {'status': 200, 'address': user_address}


@APP.route("/v{}/balance".format(VERSION), methods=['POST'])
@api_call
def balance_handler(user_address):
    """
    Get the balance of your account
    Use this call to get the balance of your account.
    ---
    tags:
    - wallet
    parameters:
      - name: X-Pubkey
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/balance,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
    responses:
      200:
        description: balance in BULs
        schema:
          properties:
            available_buls:
              type: integer
              format: int32
              minimum: 0
              description: funds available for usage in buls
          example:
            available_buls: 850
    """
    return {'available_buls': paket.get_balance(user_address)}


@APP.route("/v{}/send_buls".format(VERSION), methods=['POST'])
@api_call(['to_address', 'amount_buls'])
def send_buls_handler(user_address, to_address, amount_buls):
    """
    Transfer BULs to another address.
    Use this call to send part of your balance to another user.
    The to_address can be either a user id, or a wallet address.
    ---
    tags:
    - wallet
    parameters:
      - name: X-Pubkey
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/send_buls,to_address=address,amount_buls=amount,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
      - name: to_address
        in: formData
        default: launcher
        description: target address for transfer
        required: true
        type: string
      - name: amount_buls
        in: formData
        default: 111
        description: amount to transfer
        required: true
        type: integer
    responses:
      200:
        description: transfer request sent
    """
    return {'status': 200, 'promise': paket.send_buls(user_address, to_address, amount_buls)}


@APP.route("/v{}/launch_package".format(VERSION), methods=['POST'])
@api_call(['recipient_address', 'deadline_timestamp', 'courier_address', 'payment_buls', 'collateral_buls'])
def launch_package_handler(
        user_address, recipient_address, deadline_timestamp, courier_address, payment_buls, collateral_buls
):
    # pylint: disable=line-too-long
    """
    Launch a package.
    Use this call to create a new package for delivery.
    ---
    tags:
    - packages
    parameters:
      - name: X-Pubkey
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/launch_package,recipient_address=address,deadline_timestamp=timestamp,courier_address=address,payment_buls=buls,collateral_buls=buls,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
      - name: recipient_address
        in: formData
        default: recipient
        description: Recipient address
        required: true
        type: string
      - name: deadline_timestamp
        in: formData
        default: 9999999999
        description: Deadline timestamp
        required: true
        type: integer
        example: 1520948634
      - name: courier_address
        in: formData
        default: courier
        description: Courier address
        required: true
        type: string
      - name: payment_buls
        in: formData
        default: 10
        description: BULs promised as payment
        required: true
        type: integer
      - name: collateral_buls
        in: formData
        default: 100
        description: BULs required as collateral
        required: true
        type: integer
    responses:
      200:
        description: Package launched
        content:
          schema:
            type: string
            example: PKT-12345
          example:
            PKT-id: 1001
    """
    # pylint: enable=line-too-long
    new_paket = paket.launch_paket(
        user_address, recipient_address, deadline_timestamp, courier_address, payment_buls
    )
    db.create_package(new_paket['paket_id'], user_address, recipient_address, payment_buls, collateral_buls)
    return dict(status=200, **new_paket)


@APP.route("/v{}/accept_package".format(VERSION), methods=['POST'])
@api_call(['paket_id'])
def accept_package_handler(user_address, paket_id):
    """
    Accept a package.
    If the package requires collateral, commit it.
    If user is the package's recipient, release all funds from the escrow.
    ---
    tags:
    - packages
    parameters:
      - name: X-Pubkey
        in: header
        default: courier
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/accept_package,paket_id=id,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
      - name: paket_id
        in: formData
        description: PKT id
        required: true
        type: string
        default: 0
    responses:
      200:
        description: Package accept requested
    """
    package = db.get_package(paket_id)
    promise = paket.accept_paket(
        user_address, int(paket_id, 10), package['custodian_address'], package['collateral'])
    db.update_custodian(paket_id, user_address)
    return {'status': 200, 'promise': promise}


@APP.route("/v{}/relay_package".format(VERSION), methods=['POST'])
@api_call(['paket_id', 'courier_address', 'payment_buls'])
def relay_package_handler(user_address, paket_id, courier_address, payment_buls):
    """
    Relay a package to another courier, offering payment.
    ---
    tags:
    - packages
    parameters:
      - name: X-Pubkey
        in: header
        default: courier
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/relay_package,paket_id=id,courier_address=address,payment_buls=buls,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
      - name: paket_id
        in: formData
        description: PKT id
        required: true
        type: string
        default: 0
      - name: courier_address
        in: formData
        default: courier
        description: Courier address
        required: true
        type: string
      - name: payment_buls
        in: formData
        default: 10
        description: BULs promised as payment
        required: true
        type: integer
    responses:
      200:
        description: Package launched
        content:
          schema:
            type: string
            example: PKT-12345
          example:
            PKT-id: 1001
    """
    return {'status': 200, 'promise': paket.relay_payment(user_address, paket_id, courier_address, payment_buls)}


# pylint: disable=unused-argument
@APP.route("/v{}/my_packages".format(VERSION), methods=['POST'])
@api_call()
def my_packages_handler(user_address, show_inactive=False, from_date=None, role_in_delivery=None):
    """
    Get list of packages
    Use this call to get a list of packages.
    You can filter the list by showing only active packages, or packages originating after a certain date.
    You can also filter to show only packages where the user has a specific role, such as "launcher" or "receiver".
    ---
    tags:
    - packages
    parameters:
      - name: X-Pubkey
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/my_packages,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
      - name: show_inactive
        in: formData
        description: include inactive packages in response
        required: false
        type: boolean
        default: false
      - name: from_date
        in: formData
        description: show only packages from this date forward
        required: false
        type: string
    responses:
      200:
        description: list of packages
        schema:
          properties:
            packages:
              type: array
              items:
                $ref: '#/definitions/Package'
          example:
            - PKT-id: 1001
              Recipient-id: '@israel'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              cost: 120
              collateral: 400
              status: in transit
            - PKT-id: 1002
              Recipient-id: '@oren'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              cost: 20
              collateral: 40
              status: delivered
    """
    return {'status': 200, 'packages': db.get_packages()}
# pylint: disable=unused-argument


@APP.route("/v{}/package".format(VERSION), methods=['POST'])
@api_call()
def package_handler(user_address, paket_id):
    """
    Get a info about a single package.
    This will return additional information, such as GPS location, custodian, etc.
    ---
    tags:
    - packages
    parameters:
      - name: X-Pubkey
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/package,paket_id=id,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
      - name: paket_id
        in: formData
        description: PKT id
        required: true
        type: string
        default: 0
    definitions:
      Package:
        type: object
        properties:
          PKT-id:
              type: string
          Recipient-id:
              type: string
          send-timestamp:
              type: integer
          deadline-timestamp:
              type: integer
          cost:
              type: integer
          collateral:
              type: integer
          status:
              type: string
    responses:
      200:
        description: a single packages
        schema:
          $ref: '#/definitions/Package'
          example:
            - PKT-id: 1001
              Recipient-id: '@israel'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              cost: 120
              collateral: 400
              status: in transit
    """
    return {'status': 200, 'package': db.get_package(paket_id)}


@APP.route("/v{}/register_user".format(VERSION), methods=['POST'])
@api_call(['full_name', 'phone_number', 'paket_user'])
def register_user_handler(user_address, full_name, phone_number, paket_user):
    """
    Register a new user.
    ---
    tags:
    - users
    parameters:
      - name: X-Pubkey
        in: header
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/register_user,full_name=name,phone_number=number,paket_user=user,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
      - name: paket_user
        in: formData
        default: none
        description: User unique callsign
        required: true
        type: string
      - name: full_name
        in: formData
        default: First Last
        description: Full name of user
        required: true
        type: string
      - name: phone_number
        in: formData
        default: 123-456
        description: User phone number
        required: true
        type: string
    responses:
      201:
        description: user details registered.
    """
    return {'status': 201, 'user_details': db.update_user_details(
        user_address, full_name, phone_number, paket_user)}


@APP.route("/v{}/recover_user".format(VERSION), methods=['POST'])
@api_call
def recover_user_handler(user_address):
    """
    Recover user details.
    ---
    tags:
    - users
    parameters:
      - name: X-Pubkey
        in: header
        schema:
            type: string
            format: string
      - name: X-Footprint
        in: header
        default: http://localhost:5000/v1/recover_user,1521650747
        schema:
            type: string
            format: string
      - name: X-Signature
        in: header
        default: "0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc"
        schema:
            type: string
            format: string
    responses:
      200:
        description: user details retrieved.
    """
    return {'status': 200, 'user_details': db.get_user(user_address)}


@APP.route("/v{}/price".format(VERSION), methods=['POST'])
def price_handler():
    """
    Get buy and sell prices.
    ---
    tags:
    - wallet
    responses:
      200:
        description: buy and sell prices
        schema:
          properties:
            buy_price:
              type: integer
              format: int32
              minimum: 0
              description: price for which a BUL may me purchased
            sell_price:
              type: integer
              format: int32
              minimum: 0
              description: price for which a BUL may me sold
          example:
            {
                "status": 200,
                "buy_price": 1,
                "sell_price": 1
            }
    """
    return flask.jsonify({'status': 200, 'buy_price': 1, 'sell_price': 1})


@APP.route("/v{}/users".format(VERSION), methods=['GET'])
def users_handler():
    """
    Get a list of users and their addresses - for debug only.
    ---
    tags:
    - debug
    responses:
      200:
        description: a list of users
        schema:
          properties:
            available_buls:
              type: integer
              format: int32
              minimum: 0
              description: funds available for usage in buls
          example:
            "status": 200,
            "users": {
                "0x5E764542CC5CaB16e2a5440b60c43792a2703361": {
                "full_name": "courier",
                "paket_user": "courier",
                "phone_number": "123-456"
                },
                "0xC87CE45Af751367300bb8ea62B2f5442337211bE": {
                "full_name": "recipient",
                "paket_user": "recipient",
                "phone_number": "123-456"
                },
                "0xb91927C0F744aB701eb7dBF0bCF30a77F14c922C": {
                "full_name": "launcher",
                "paket_user": "launcher",
                "phone_number": "123-456"
                },
                "0xe77a8Ec88B5854B677C1B6Cc5447b199ACc1A94e": {
                "full_name": "owner",
                "paket_user": "owner",
                "phone_number": "123-456"
                }
            }
    """
    return flask.jsonify({'status': 200, 'users': db.get_users()})


@APP.route("/v{}/packages".format(VERSION), methods=['GET'])
def packages_handler():
    """
    Get list of packages - for debug only.
    ---
    tags:
    - debug
    responses:
      200:
        description: list of packages
        schema:
          properties:
            packages:
              type: array
              items:
                $ref: '#/definitions/Package'
          example:
            - PKT-id: 1001
              Recipient-id: '@israel'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              cost: 120
              collateral: 400
              status: in transit
            - PKT-id: 1002
              Recipient-id: '@oren'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              cost: 20
              collateral: 40
              status: delivered
    """
    return flask.jsonify({'status': 200, 'packages': db.get_packages()})


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
    """Custom error handler for rate limiting."""
    error = 'Rate limit ({}) exceeded'.format(error.description)
    LOGGER.warning(error)
    return flask.make_response(flask.jsonify({'status': 429, 'error': error}), 429)


def init_sandbox():
    """Initialize database with debug values and fund users. For debug only."""
    db.init_db()
    for paket_user, address in {
            'owner': paket.OWNER, 'launcher': paket.LAUNCHER, 'recipient': paket.RECIPIENT, 'courier': paket.COURIER
    }.items():
        try:
            db.create_user(address)
            db.update_user_details(address, paket_user, '123-456', paket_user)
            paket.send_buls(paket.OWNER, address, 1000)
            LOGGER.debug("Created and funded user %s", paket_user)
        except db.DuplicateUser:
            LOGGER.debug("User %s already exists", paket_user)
