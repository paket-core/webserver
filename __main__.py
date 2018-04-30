"""Run test webserver."""
import sys
import os.path

import flasgger
import flask

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# pylint: disable=wrong-import-position
# Python imports are silly.
import webserver
import webserver.validation
# pylint: enable=wrong-import-position

VERSION = 1
BLUEPRINT = flask.Blueprint('test', __name__)
SWAGGER_CONFIG = {
    'title': 'Webserver demo',
    'uiversion': 3,
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
        'rule_filter': lambda rule: True,  # all in
        'model_filter': lambda tag: True,  # all in
    }],
    'description': 'Not much here.'
}
TEST_SWAGGER = {
    "parameters": [
        {
            "name": "palette",
            "in": "path",
            "type": "string",
            "enum": [
                "all",
                "rgb",
                "cmyk"
                ],
            "required": "true",
            "default": "all"
        }
    ],
    "definitions": {
        "Palette": {
            "type": "object",
            "properties": {
                "palette_name": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/Color"
                    }
                }
            }
        },
        "Color": {"type": "string"}
    },
    "responses": {
        "200": {
            "description": "A list of colors (may be filtered by palette)",
            "schema": {
                "$ref": "#/definitions/Palette"},
            "examples": {
                "rgb": [
                    "red",
                    "green",
                    "blue"
                ]
            }
        }
    }
}


@BLUEPRINT.route("/v{}/test".format(VERSION), methods=['GET', 'POST'])
@flasgger.swag_from(TEST_SWAGGER)
@webserver.validation.call(['transaction'])
def test_handler():
    """Just a test."""
    return {'status': 200, 'message': 'success!'}


webserver.run(BLUEPRINT, SWAGGER_CONFIG, True)
