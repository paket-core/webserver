'Web JSON swagger API to PaKeT smart contract.'
import os

import flask
import flask_cors
import flask_limiter.util
import flask_swagger

import paket

VERSION = '1'

APP = flask.Flask('PaKeT')
flask_cors.CORS(APP)
APP.config['SECRET_KEY'] = os.environ.get('PAKET_SESSIONS_KEY', os.urandom(24))
STATIC_DIRS = ['static', 'swagger-ui/dist']
DEFAULT_LIMIT = os.environ.get('PAKET_SERVER_LIMIT', '100 per minute')
LIMITER = flask_limiter.Limiter(APP, key_func=flask_limiter.util.get_remote_address, default_limits=[DEFAULT_LIMIT])

@APP.route("/v{}/balance/<user>".format(VERSION), methods=['GET', 'POST'])
def balance_endpoint(user):
    """
      Get the balance of your account
      Use this call to get the balance of our account.
      ---
      tags:
        - user-calls
      parameters:
        - user: the user name
          in: URL
          description: the user's name
          required: true
          type: string
          format: string
          default: debug

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
    """
    return flask.jsonify({'available_bulls': 850})


@APP.route('/spec.json')
def spec_endpoint():
    'Swagger.'
    swag = flask_swagger.swagger(APP)
    swag['info']['version'] = VERSION
    swag['info']['title'] = 'PaKeT'
    swag['info']['description'] = '''
This is a cool thing.
'''
    return flask.jsonify(swag), 200

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
            path, VERSION, path[1])
    return flask.jsonify({'code': 403, 'error': error}), 403
