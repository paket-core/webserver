'Web JSON swagger API to PaKeT smart contract.'
import collections
import functools
import os

import flasgger
import flask
import flask_limiter.util

import paket
import logger

VERSION = '1'
LOGGER = logger.logging.getLogger('pkt.api')
logger.setup()

APP = flask.Flask('PaKeT')
APP.config['SECRET_KEY'] = os.environ.get('PAKET_SESSIONS_KEY', os.urandom(24))
STATIC_DIRS = ['static', 'swagger-ui/dist']
DEFAULT_LIMIT = os.environ.get('PAKET_SERVER_LIMIT', '100 per minute')
LIMITER = flask_limiter.Limiter(APP, key_func=flask_limiter.util.get_remote_address, default_limits=[DEFAULT_LIMIT])

APP.config['SWAGGER'] = {
    'uiversion': 3
    }

template = {
  "swagger": "3.0",

  "info": {
    "title": "PaKeT API",
    "description": "This is a cool thing.",
    "contact": {
      "responsibleOrganization": "ME",
      "responsibleDeveloper": "Me",
      "email": "me@me.com",
      "url": "www.me.com",
    },
    "termsOfService": "http://me.com/terms",
    "version": VERSION
  },

  "securityDefinitions": {
    "an_api_key thingy": {
      "type": "apiKey",
      "name": "api_key_name",
      "in": "header"
    },
    "oauth": {
      "type": "oauth2",
      "authorizationUrl": "https://github.com/login/oauth/authorize",
      "tokenUrl": "https://github.com/login/oauth/access_token",
      "flow": "authorizationCode",
      "scopes": {
        "read:players": "read player data"
      }
    },
  },
  #"host": "mysite.com",  # overrides localhost:500
  #"basePath": "/api",  # base bash for blueprint registration
  "schemes": [
    "http",
  ],
}

flasgger.Swagger(APP, template=template)


class MissingFields(Exception):
    'This denotes missing field in args.'


class BadBulNumberField(Exception):
    'This denotes invalid BUL number field.'


def validate_fields(fields, required_fields):
    'Raise exception if there are missing fields.'
    if required_fields is None:
        required_fields = set()
    missing_fields = required_fields - fields
    if missing_fields:
        raise MissingFields(', '.join(missing_fields))


def validate_values(args):
    'Raise exception if a "_bulls" field is not a valid integer.'
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
    return args


def validate_user(user_id):
    'Raise exception if user is invalid.'
    # This will support OAuth, probably.
    LOGGER.warning("not validating user %s", user_id)


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
            kwargs = flask.request.values
            validate_fields(set(kwargs.keys()), required_fields)
            kwargs = validate_values(kwargs)
            response = handler(**kwargs.to_dict())
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


@APP.route("/v{}/balance".format(VERSION))
@validate_call({'user_id'})
def balance_endpoint(user_id):
    '''
      Get the balance of your account
      Use this call to get the balance of our account.
      ---
      tags:
        - user-calls
      parameters:
        - in: query
          name: user_id
          description: the user's unique ID
          required: true
          type: string
          default: owner

      responses:
        200:
          description: Status provided.
          schema:
            properties:
              available_bulls:
                type: integer
                format: int32
                minimum: 0
                description: funds available for usage in buls
            example:
              code: 200
              available_bulls: 850
    '''
    balance = paket.get_balance(user_id)
    return {'available_bulls': balance or 0}


@APP.route("/v{}/transfer".format(VERSION))
@validate_call({'address', 'amount'})
def transfer_endpoint(address, amount):
    'Put swagger shit here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/packages".format(VERSION))
@validate_call()
def packages_endpoint(show_inactive=False, from_date=None, role_in_delivery=None):
    'Put swagger shit here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/launch".format(VERSION))
@validate_call({'address', 'amount'})
def launch_endpoint():
    'Put swagger shit here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/accept".format(VERSION))
@validate_call
def accept_endpoint():
    'Put swagger shit here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/address".format(VERSION))
@validate_call
def address_endpoint():
    'Put swagger shit here.'
    return {'error': 'Not implemented', 'status': 501}


@APP.route("/v{}/price".format(VERSION))
@validate_call
def price_endpoint():
    'Put swagger shit here.'
    return {'error': 'Not implemented', 'status': 501}


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
    LOGGER.warning('in catchall')
    for directory in STATIC_DIRS:
        if os.path.isfile(os.path.join(directory, path)):
            return flask.send_from_directory(directory, path)
    error = "Forbidden: /{}".format(path)
    if path[0] == 'v' and path[2] == '/' and path[1].isdigit and path[1] != VERSION:
        error = "/{} - you are trying to access an unsupported version of the API ({}), please use /v{}/".format(path, VERSION, VERSION)
    return flask.jsonify({'status': 403, 'error': error}), 403
