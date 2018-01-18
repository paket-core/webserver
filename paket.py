#!/usr/bin/env python3
'API to PaKeT smart contract.'
import json
import os
import sys

import flask
import flask_cors
import flask_limiter.util
import flask_swagger
import web3
import werkzeug.serving
# pylint: disable=no-member
# Pylint has a hard time with dynamic members.

VERSION = '1'
APP = flask.Flask('PaKeT')
APP.config['SECRET_KEY'] = os.environ.get('PAKET_SESSIONS_KEY', os.urandom(24))
STATIC_DIRS = ['static', 'swagger-ui/dist']
GLOBAL_LIMIT = os.environ.get('PAKET_SERVER_LIMIT', '100 per minute')
LIMITER = flask_limiter.Limiter(APP, key_func=flask_limiter.util.get_remote_address, global_limits=[GLOBAL_LIMIT])
flask_cors.CORS(APP)

RPC_PROTOCOL = 'http'
RPC_HOST = 'localhost'
RPC_PORT = 8545
ADDRESS = os.environ['PAKET_ADDRESS']
ABI = json.loads(os.environ['PAKET_ABI'])

def get_contract(address, abi, protocol=RPC_PROTOCOL, host=RPC_HOST, port=RPC_PORT):
    'Get a contract.'
    return web3.Web3(
        web3.HTTPProvider("{}://{}:{}".format(protocol, host, port))
    ).eth.contract(address=address, abi=abi)

PAKET = get_contract(ADDRESS, ABI)
APP.logger.info("Connected to contract at %s, owner: %s", ADDRESS, PAKET.call().owner())

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
