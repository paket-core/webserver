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

APP = flask.Flask('PaKeT')
APP.config['SECRET_KEY'] = os.environ.get('PAKET_SESSIONS_KEY', os.urandom(24))
STATIC_DIRS = ['static']
DEFAULT_LIMIT = os.environ.get('PAKET_SERVER_LIMIT', '100 per minute')
LIMITER = flask_limiter.Limiter(APP, key_func=flask_limiter.util.get_remote_address, default_limits=[DEFAULT_LIMIT])

APP.config['SWAGGER'] = {
    'title': 'PaKeT API',
    'uiversion': 3,
    'specs_route': '/',
    "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,  # all in
                "model_filter": lambda tag: True,  # all in
            }
        ],
}
flasgger.Swagger(APP, template={
    "swagger": "2.0",
    "info": {
        "title": "PaKeT API",
        "description": "Web API Server for The PaKeT Project",
        "contact": {
            "name": "Israel Levin",
            "email": "Israel@paket.global",
            "url": "www.paket.global",
        },
        "version": VERSION,
        "license": {
            "name": "Apache 2.0",
            "url": "http://www.apache.org/licenses/LICENSE-2.0.html"
          },
    },
    "schemes": [
        "http",
        "https"
    ],
})


class MissingFields(Exception):
    """Missing field in args."""


class BadBulNumberField(Exception):
    """Invalid BUL number field."""


class BadAddressField(Exception):
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
                raise BadBulNumberField("the value of {}({}) is not an integer".format(key, value))
            if int_val >= 10 ** 10:
                raise BadBulNumberField("the value of {}({}) is too large".format(key, value))
            elif int_val < 0:
                raise BadBulNumberField("the value of {}({}) is less than zero".format(key, value))
            kwargs[key] = int_val
        elif key.endswith('_address'):
            # For debug purposes, we allow user IDs as addresses.
            LOGGER.warning("Attempting conversion of user ID %s to address", value)
            kwargs[key] = db.get_user_address(value)
            if not paket.W3.isAddress(kwargs[key]):
                raise BadAddressField("value of {} is not a valid address".format(key))
    return kwargs


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
            kwargs['user_address'] = db.get_user_address(flask.request.headers.get('X-User-ID'))
            response = handler(**kwargs)
        except MissingFields as exception:
            response = {'status': 400, 'error': "Request does not contain field(s): {}".format(exception)}
        except BadBulNumberField as exception:
            response = {'status': 400, 'error': str(exception)}
        except db.UnknownUser as exception:
            response = {'status': 403, 'error': str(exception)}
        except Exception as exception:
            LOGGER.exception("Unknown validation exception. Headers: %s", flask.request.headers)
            response['debug'] = str(exception)
        if 'error' in response:
            LOGGER.warning(response['error'])
        return flask.make_response(flask.jsonify(response), response.get('status', 200))

    return _api_call


@APP.route("/v{}/balance".format(VERSION))
@api_call
def balance_handler(user_address):
    """
    Get the balance of your account
    Use this call to get the balance of your account.
    ---
    tags:
    - wallet
    parameters:
      - name: X-User-ID
        in: header
        default: owner
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


@APP.route("/v{}/transfer_buls".format(VERSION))
@api_call(['to_address', 'amount_buls'])
def transfer_buls_handler(user_address, to_address, amount_buls):
    """
    Transfer BULs to another address.
    Use this call to send part of your balance to another user.
    The to_address can be either a user id, or a wallet address.
    ---
    tags:
    - wallet
    parameters:
      - name: X-User-ID
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: to_address
        in: query
        description: target address for transfer
        required: true
        type: string
      - name: amount_buls
        in: query
        description: amount to transfer
        required: true
        type: integer
    responses:
      200:
        description: transfer request sent
    """
    return {'status': 200, 'promise': paket.transfer_buls(user_address, to_address, amount_buls)}


@APP.route("/v{}/launch_package".format(VERSION))
@api_call(['recipient_address', 'deadline_timestamp', 'courier_address', 'payment_buls'])
def launch_handler(user_address, recipient_address, deadline_timestamp, courier_address, payment_buls):
    """
    Launch a package.
    Use this call to create a new package for delivery.
    ---
    tags:
    - packages
    parameters:
      - name: X-User-ID
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: recipient_address
        in: query
        default: recipient
        description: Recipient address
        required: true
        type: string
      - name: deadline_timestamp
        in: query
        default: 9999999999
        description: Deadline timestamp
        required: true
        type: integer
        example: 1520948634
      - name: courier_address
        in: query
        default: courier
        description: Courier address
        required: true
        type: string
      - name: payment_buls
        in: query
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
    return dict(status=200, **paket.launch_paket(
        user_address, recipient_address, deadline_timestamp, courier_address, payment_buls
    ))


# pylint: disable=unused-argument
@APP.route("/v{}/packages".format(VERSION))
@api_call()
def packages_handler(show_inactive=False, from_date=None, role_in_delivery=None):
    """
    Get list of packages
    Use this call to get a list of packages.
    You can filter the list by showing only active packages, or packages originating after a certain date.
    You can also filter to show only packages where the user has a specific role, such as "launcher" or "receiver".
    ---
    tags:
    - packages
    parameters:
      - name: X-User-ID
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: show_inactive
        in: query
        description: include inactive packages in response
        required: false
        type: boolean
        default: false
      - name: from_date
        in: query
        description: show only packages from this date forward
        required: false
        type: string
      - name: collateral_buls
        in: query
        description: BULs required as collateral
        required: true
        type: integer
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
    return {'status': 501, 'error': 'Not implemented'}


@APP.route("/v{}/package".format(VERSION))
@api_call()
def package_handler(package_id):
    """
    Get a info about a single package.
    This will return additional information, such as GPS location, custodian, etc.
    ---
    tags:
    - packages
    parameters:
      - name: X-User-ID
        in: header
        default: owner
        schema:
            type: string
            format: string
      - name: package_id
        in: query
        description: PKT id
        required: true
        type: integer
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
    return {'status': 501, 'error': 'Not implemented'}


@APP.route("/v{}/accept".format(VERSION))
@api_call
def accept_handler():
    """Put swagger YAML here."""
    return {'status': 501, 'error': 'Not implemented'}


@APP.route("/v{}/wallet_address".format(VERSION))
@api_call
def wallet_address_handler(user_address):
    """
        Get the address of the BULs. This addressed can be used to send BULs to.
        ---
        tags:
        - wallet
        parameters:
          - name: X-User-ID
            in: header
            default: owner
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
    return {'status': 501, 'error': 'Not implemented'}


@APP.route("/v{}/price".format(VERSION))
@api_call
def price_handler():
    """Put swagger YAML here."""
    return {'status': 501, 'error': 'Not implemented'}


@APP.route("/v{}/users".format(VERSION))
def users_handler():
    """
    Get a list of users and their addresses - for debug only.
    ---
    tags:
    - debug
    parameters:
      - name: X-User-ID
        in: header
        default: owner
        schema:
            type: string
            format: string
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
            {
                "status": 200,
                "users": [
                    [
                    "owner",
                    "0x27936e0AFe9634E557c17aeA7FF7885D4D2901b6"
                    ],
                    [
                    "launcher",
                    "0xa5F478281ED1b94bD7411Eb2d30255F28b833e28"
                    ],
                    [
                    "recipient",
                    "0x00196f888b3eDa8C6F4a116511CAFeD93008763f"
                    ],
                    [
                    "courier",
                    "0x498e32Ae4B84f96CDD24a2d5b7270A15Ad8d9a26"
                    ]
                ]
            }
    """
    return flask.jsonify({'users': db.get_users()})


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
