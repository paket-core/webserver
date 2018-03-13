'Web JSON swagger API to PaKeT smart contract.'
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
    'info': {
        'title': 'PaKeT API',
        'description': 'This is a cool thing.',
        'version': VERSION}}

flasgger.Swagger(APP)


class MissingFields(Exception):
    'Missing field in args.'


class BadBulNumberField(Exception):
    'Invalid BUL number field.'


class BadAddressField(Exception):
    'Invalid address field.'


def check_missing_fields(fields, required_fields):
    'Raise exception if there are missing fields.'
    if required_fields is None:
        required_fields = set()
    missing_fields = set(required_fields) - set(fields)
    if missing_fields:
        raise MissingFields(', '.join(missing_fields))


def check_and_fix_values(kwargs):
    '''
    Raise exception for invalid values.
    "_bulls" fields must be valid integers.
    "_address" fields must be valid addresses.
    '''
    for key, value in kwargs.items():
        if key.endswith('_bulls'):
            try:
                # Cast to str before casting to int to make sure floats fail.
                int_val = int(str(value))
            except ValueError:
                raise BadBulNumberField("the value of {}({}) is not an integer".format(key, value))
            if int_val >= 10**9:
                raise BadBulNumberField("the value of {}({}) is too large".format(key, value))
            elif int_val < 0:
                raise BadBulNumberField("the value of {}({}) is less than zero".format(key, value))
            kwargs[key] = int_val
        elif key.endswith('_address'):
            # For debug purposes, we allow user IDs as addresses.
            LOGGER.warning("Attemting conversion of user ID %s to address", value)
            kwargs[key] = paket.get_user_address(value)
            if not paket.W3.isAddress(kwargs[key]):
                raise BadAddressField("value of {} is not a valid address".format(key))
    return kwargs

def optional_arg_decorator(decorator):
    'A decorator for decorators than can accept optional arguments.'
    @functools.wraps(decorator)
    def wrapped_decorator(*args, **kwargs):
        'A wrapper to return a filled up function in case arguments are given.'
        if len(args) == 1 and not kwargs and callable(args[0]):
            return decorator(args[0])
        return lambda decoratee: decorator(decoratee, *args, **kwargs)
    return wrapped_decorator


# Since this is a decorator the handler argument will never be None, it is
# defined as such only to comply with python's syntactic sugar.
@optional_arg_decorator
def api_call(handler=None, required_fields=None):
    '''
    A decorator to handle all API calls: extracts arguments, validates them,
    fixes them, handles authentication, and then passes them to the handler,
    dealing with exceptions and returning a valid response.
    '''
    @functools.wraps(handler)
    def _api_call(*args, **kwargs):
        # pylint: disable=broad-except
        # If anything fails, we want to catch it here.
        try:
            kwargs = flask.request.values.to_dict()
            check_missing_fields(kwargs.keys(), required_fields)
            kwargs = check_and_fix_values(kwargs)
            kwargs['user_address'] = db.get_address(flask.request.headers.get('X-User-ID'))
            response = handler(**kwargs)
        except MissingFields as exception:
            response = {'status': 400, 'error': "Request does not contain field(s): {}".format(exception)}
        except BadBulNumberField as exception:
            response = {'status': 400, 'error': str(exception)}
        except db.UnknownUser as exception:
            response = {'status': 403, 'error': str(exception)}
        except Exception:
            LOGGER.exception("Unknown validation exception. Headers: %s", flask.request.headers)
        if 'error' in response:
            LOGGER.warning(response['error'])
        return flask.make_response(flask.jsonify(response), response.get('status', 200))
    return _api_call


@APP.route("/v{}/balance".format(VERSION))
@api_call
def balance_endpoint(user_address):
    '''
    Get the balance of your account
    Use this call to get the balance of our account.
    ---
    parameters:
      - name: X-User-ID
        in: header
        schema:
            type: string
            format: string
    responses:
      200:
        description: balance in BULs
        schema:
          properties:
            available_bulls:
              type: integer
              format: int32
              minimum: 0
              description: funds available for usage in buls
          example:
            available_bulls: 850
    '''
    return {'available_bulls': paket.get_balance(user_address)}


@APP.route("/v{}/transfer_bulls".format(VERSION))
@api_call(['to_address', 'amount_bulls'])
def transfer_bulls_endpoint(user_address, to_address, amount_bulls):
    '''
    Transfer BULs to another address.
    ---
    parameters:
      - name: X-User-ID
        in: header
        schema:
            type: string
            format: string
      - name: to_address
        in: query
        description: target address for transfer
        required: true
        type: string
      - name: amount_bulls
        in: query
        description: amount to transfer
        required: true
        type: integer
    responses:
      200:
        description: transfer request sent
    '''
    return {'promise': paket.transfer(user_address, to_address, amount_bulls), 'status': 200}


@APP.route("/v{}/packages".format(VERSION))
@api_call()
def packages_endpoint(show_inactive=False, from_date=None, role_in_delivery=None):
    '''
    Get list of packages
    ---
    parameters:
      - name: X-User-ID
        in: header
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
    responses:
      200:
        description: list of packages
        schema:
          properties:
            packagess:
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
    '''
    return {'error': 'Not implemented', 'status': 501}

@APP.route("/v{}/package".format(VERSION))
@api_call()
def package_endpoint(package_id):
    '''
    Get a single package
    ---
    parameters:
      - name: X-User-ID
        in: header
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
    '''
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/launch".format(VERSION))
@api_call(['to_address', 'payment_bulls', 'collateral_bulls'])
def launch_endpoint():
    '''
    Launch a package
    ---
    parameters:
      - name: X-User-ID
        in: header
        schema:
            type: string
            format: string
      - name: to_address
        in: query
        description: Receiver address
        required: true
        type: string
        default: '@oren'
    responses:
      200:
        description: Package launched
        content:
          schema:
            type: string
            example: PKT-12345
          example:
            - PKT-id: 1001
              Recipient-id: '@israel'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              cost: 120
              collateral: 400
              status: in transit
    '''
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/accept".format(VERSION))
@api_call
def accept_endpoint():
    'Put swagger YAML here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/address".format(VERSION))
@api_call
def address_endpoint():
    'Put swagger YAML here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/price".format(VERSION))
@api_call
def price_endpoint():
    'Put swagger YAML here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/users".format(VERSION))
@api_call
def users_endpoint(user_address=None):
    '''
    Get a list of users and their addresses - for debug only.
    ---
    parameters:
      - name: X-User-ID
        in: header
        schema:
            type: string
            format: string
    responses:
      200:
        description: a list of users
        schema:
          properties:
            available_bulls:
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
    '''
    return {'users': db.get_users(), 'status': 200}


@APP.errorhandler(429)
def ratelimit_handler(error):
    'Custom error for rate limiter.'
    msg = 'Rate limit exceeded. Allowed rate: {}'.format(error.description)
    LOGGER.info(msg)
    return flask.make_response(flask.jsonify({'status': 429, 'error': msg}), 429)


@APP.route('/')
@APP.route('/<path:path>', methods=['GET', 'POST'])
@LIMITER.limit(limit_value="2000 per second")
def catch_all_endpoint(path='index.html'):
    'All undefined endpoints try to serve from the static directories.'
    for directory in STATIC_DIRS:
        if os.path.isfile(os.path.join(directory, path)):
            return flask.send_from_directory(directory, path)
    error = "Forbidden: /{}".format(path)
    if path[0] == 'v' and path[2] == '/' and path[1].isdigit and path[1] != VERSION:
        error = "/{} - you are trying to access an unsupported version of the API ({}), please use /v{}/".format(
            path, VERSION, VERSION)
    return flask.jsonify({'status': 403, 'error': error}), 403
