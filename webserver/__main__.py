"""Run test webserver."""
import sys
import os.path

import flasgger
import flask

# Python imports are silly.
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# pylint: disable=wrong-import-position
import webserver.validation
# pylint: enable=wrong-import-position

VERSION = 1
BLUEPRINT = flask.Blueprint('test', __name__)
SWAGGER_CONFIG = {
    'title': 'Webserver demo',
    'uiversion': 2,
    'specs_route': '/',
    'info': {
        'title': 'Just a demo',
        'description': 'webserver package at work',
        'contact': {
            'name': 'The PaKeT Project',
            'email': 'israel@paket.global',
            'url': 'https://paket.global',
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
    }],
    'description': 'Not much here.'
}

SIGN = {
    'parameters': [
        {
            'name': 'seed',
            'in': 'formData',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'fingerprint',
            'in': 'formData',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
    ],
    'responses': {
        '201': {
            'description': 'Base64 encoded signature.'
        }
    }
}


CHECK_SIGNATURE = {
    'parameters': [
        {
            'name': 'Pubkey',
            'in': 'header',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Fingerprint',
            'in': 'header',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Signature',
            'in': 'header',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
    ],
    'responses': {
        '200': {
            'description': 'Signature verified.'
        }
    }
}


@BLUEPRINT.route("/v{}/sign".format(VERSION), methods=['POST'])
@flasgger.swag_from(SIGN)
@webserver.validation.call(['seed', 'fingerprint'])
def sign_handler(fingerprint, seed):
    """Sign a fingerprint."""
    return {'status': 201, 'signature': webserver.validation.sign_fingerprint(fingerprint, seed)}


@BLUEPRINT.route("/v{}/check_signature".format(VERSION), methods=['GET'])
@flasgger.swag_from(CHECK_SIGNATURE)
@webserver.validation.call(require_auth=True)
def check_signature_handler(user_pubkey):
    """Check a signature."""
    return {'status': 200, 'message': "signature verified for {}".format(user_pubkey)}


webserver.run(BLUEPRINT, SWAGGER_CONFIG)
