'Web JSON swagger API to PaKeT smart contract.'
import collections
import functools
import os

import flasgger
import flask
import flask_dance.contrib.github
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

#from flask import Flask, redirect, url_for
#from flask_dance.contrib.github import make_github_blueprint, github
BLUEPRINT = flask_dance.contrib.github.make_github_blueprint(
    client_id=os.environ['GITHUB_CLIENT_ID'],
    client_secret=os.environ['GITHUB_CLIENT_SECRET'])
APP.register_blueprint(BLUEPRINT, url_prefix="/login")

APP.config['SWAGGER'] = {
    'title': 'PaKeT API',
    'uiversion': 3,
    'specs_route': '/',
    'info': {
        'title': 'PaKeT API',
        'description': 'This is a cool thing.',
        'version': VERSION},
    'securityDefinitions': {
        'oauth': {
            'type': 'oauth2',
            'authorizationUrl': '/login/github/authorized',
            'flow': 'authorizationCode'}}}
flasgger.Swagger(APP)


class MissingFields(Exception):
    'This denotes missing field in args.'


class BadBulNumberField(Exception):
    'This denotes invalid BUL number field.'


class BadAddressField(Exception):
    'This denotes invalid address field.'


def validate_fields(fields, required_fields):
    'Raise exception if there are missing fields.'
    if required_fields is None:
        required_fields = set()
    missing_fields = required_fields - fields
    if missing_fields:
        raise MissingFields(', '.join(missing_fields))


def validate_values(args):
    '''
    Raise exception for invalid values.
    "_bulls" fields must be valid integers.
    "_address" fields must be valid addresses.
    For debug purposes, we allow addresses as user IDs.
    '''
    for key, value in args.items():
        if key.endswith('_bulls'):
            try:
                # We cast to str so floats will fail.
                int_val = int(str(value))
            except ValueError:
                raise BadBulNumberField("{} is not an integer".format(key))
            if int_val > 9999999999:
                raise BadBulNumberField("value of {} is too large".format(key))
            elif int_val < 0:
                raise BadBulNumberField("value of {} is smaller than zero".format(key))
            args[key] = int_val
        elif key.endswith('_address'):
            args[key] = paket.get_user_address(value)
            if not paket.W3.isAddress(args[key]):
                raise BadAddressField("value of {} is not a valid address".format(key))
    return args


def get_user_id():
    'Get current user.'
    # For debug purposed, allow defining a user ID in the header.
    if flask.request.headers.get('X-User-ID'):
        return flask.request.headers.get('X-User-ID')

    if flask_dance.contrib.github.github.authorized:
        resp = flask_dance.contrib.github.github.get('/user')
        if resp.ok:
            return resp.json
    return False

def get_user_address():
    'Get Current user address.'
    return paket.get_user_address(get_user_id())


def optional_args_decorator(decorator):
    'A decorator decorator, allowing a decorator to be used with or without arg.'
    @functools.wraps(decorator)
    def decorated(*args, **kwargs):
        'Differentiate between arg-less and arg-full calls to the decorator.'
        if len(args) == 1 and not kwargs and isinstance(args[0], collections.Callable):
            return decorator(args[0])
        return lambda decoratee: decorator(decoratee, *args, **kwargs)
    return decorated


@optional_args_decorator
def validate_call(handler=None, required_fields=None):
    '''
    Validate an API call and pass it to a handler function.
    Note that if required_fields is given it has to be a set.
    Also not that handler is defaulted to None so as not to screw up the
    syntactic sugar of the decorator - otherwise we will need to specify the
    handler whenever the decorator receives arguments.
    '''
    @functools.wraps(handler)
    def _validate_call():
        # Default values.
        response = {'status': 500, 'error': 'Internal Server Error'}
        # pylint: disable=broad-except
        # If anything fails, we want to log it and fail gracefully.
        try:
            kwargs = flask.request.values.to_dict()
            validate_fields(set(kwargs.keys()), required_fields)
            kwargs = validate_values(kwargs)
            kwargs['user_address'] = kwargs.get('user_address', get_user_address())
            if kwargs['user_address']:
                response = handler(**kwargs)
            else:
                response = {'status': 403, 'error': 'Must be logged in with an existing user'}
        except MissingFields as exception:
            response = {'status': 400, 'error': "Request does not contain field(s): {}".format(exception)}
        except BadBulNumberField as exception:
            response = {'status': 400, 'error': str(exception)}
        except Exception:
            LOGGER.exception("Unknown validation exception. Headers: %s", flask.request.headers)
        if 'error' in response:
            LOGGER.warning(response['error'])
        return flask.make_response(flask.jsonify(response), response.get('status', 200))
    return _validate_call


@APP.route('/login')
def login():
    'OAuth login.'
    if not flask_dance.contrib.github.github.authorized:
        return flask.redirect(flask.url_for("github.login"))
    resp = flask_dance.contrib.github.github.get("/user")
    assert resp.ok
    return "You are @{login} on GitHub".format(login=resp.json()["login"])


@APP.route("/v{}/balance".format(VERSION))
@validate_call
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
@validate_call({'to_address', 'amount_bulls'})
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
@validate_call()
def packages_endpoint(show_inactive=False, from_date=None, role_in_delivery=None):
    '''
    Get list of packages
    ---
    parameters:
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
@validate_call()
def package_endpoint(package_id):
    '''
    Get a single package
    ---
    parameters:
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
@validate_call({'receiver-id', })
def launch_endpoint():
    '''
    Launch a package
    ---
    parameters:
      - name: receiver-id
        in: query
        description: Receiver id
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
@validate_call
def accept_endpoint():
    'Put swagger YAML here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/address".format(VERSION))
@validate_call
def address_endpoint():
    'Put swagger YAML here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/price".format(VERSION))
@validate_call
def price_endpoint():
    'Put swagger YAML here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/users".format(VERSION))
@validate_call
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
