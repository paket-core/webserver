"""JSON swagger API to PaKeT."""
import logging

import flask
from flasgger import swag_from

import api.validation
import db
import paket

VERSION = '1'
SWAGGER_DIR = 'swagfiles'
LOGGER = logging.getLogger('pkt.api.routes')
BLUEPRINT = flask.Blueprint('api.routes', __name__)
SWAGGER_CONFIG = {
    'title': 'PaKeT API',
    'uiversion': 2,
    'specs_route': '/',
    'info': {
        'title': 'The PaKeT http server API',
        'description': 'Web API Server for The PaKeT Server',
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
}
with open("api/{}/description.txt".format(SWAGGER_DIR)) as description_file:
    SWAGGER_CONFIG['info']['description'] = description_file.read()


# pylint: disable=missing-docstring
# See documentation in swagfiles.


# Wallet routes.


@BLUEPRINT.route("/v{}/submit_transaction".format(VERSION), methods=['POST'])
@swag_from("{}/submit_transaction.yml".format(SWAGGER_DIR))
@api.validation.call(['transaction'])
def submit_transaction_handler(user_pubkey, transaction):
    return {'status': 200, 'transaction': paket.submit_transaction_envelope(user_pubkey, transaction)}


@BLUEPRINT.route("/v{}/bul_account".format(VERSION), methods=['GET'])
@swag_from("{}/bul_account.yml".format(SWAGGER_DIR))
@api.validation.call(['queried_pubkey'])
def bul_account_handler(queried_pubkey):
    return dict(status=200, **paket.get_bul_account(queried_pubkey))


@BLUEPRINT.route("/v{}/send_buls".format(VERSION), methods=['POST'])
@swag_from("{}/send_buls.yml".format(SWAGGER_DIR))
@api.validation.call(['to_pubkey', 'amount_buls'], require_auth=True)
def send_buls_handler(user_pubkey, to_pubkey, amount_buls):
    return {'status': 201, 'transaction': paket.send_buls(user_pubkey, to_pubkey, amount_buls)}


@BLUEPRINT.route("/v{}/prepare_send_buls".format(VERSION), methods=['GET'])
@swag_from("{}/prepare_send_buls.yml".format(SWAGGER_DIR))
@api.validation.call(['from_pubkey', 'to_pubkey', 'amount_buls'])
def prepare_send_buls_handler(from_pubkey, to_pubkey, amount_buls):
    return {'status': 200, 'transaction': paket.prepare_send_buls(from_pubkey, to_pubkey, amount_buls)}


@BLUEPRINT.route("/v{}/price".format(VERSION), methods=['GET'])
@swag_from("{}/price.yml".format(SWAGGER_DIR))
def price_handler():
    return flask.jsonify({'status': 200, 'buy_price': 1, 'sell_price': 1})


# Package routes.


@BLUEPRINT.route("/v{}/launch_package".format(VERSION), methods=['POST'])
@swag_from("{}/launch_package.yml".format(SWAGGER_DIR))
@api.validation.call(
    ['recipient_pubkey', 'courier_pubkey', 'deadline_timestamp', 'payment_buls', 'collateral_buls'], require_auth=True)
def launch_package_handler(
        user_pubkey, recipient_pubkey, courier_pubkey, deadline_timestamp, payment_buls, collateral_buls
):
    escrow_address, refund_transaction, payment_transaction = paket.launch_paket(
        user_pubkey, recipient_pubkey, courier_pubkey, deadline_timestamp, payment_buls, collateral_buls
    )
    return {
        'status': 200, 'escrow_address': escrow_address,
        'refund_transaction': refund_transaction, 'payment_transaction': payment_transaction}


@BLUEPRINT.route("/v{}/accept_package".format(VERSION), methods=['POST'])
@swag_from("{}/accept_package.yml".format(SWAGGER_DIR))
@api.validation.call(['paket_id'], require_auth=True)
def accept_package_handler(user_pubkey, paket_id, payment_transaction=None):
    paket.accept_package(user_pubkey, paket_id, payment_transaction)
    return {'status': 200}


@BLUEPRINT.route("/v{}/relay_package".format(VERSION), methods=['POST'])
@swag_from("{}/relay_package.yml".format(SWAGGER_DIR))
@api.validation.call(['paket_id', 'courier_pubkey', 'payment_buls'], require_auth=True)
def relay_package_handler(user_pubkey, paket_id, courier_pubkey, payment_buls):
    return {'status': 200, 'transaction': paket.relay_payment(user_pubkey, paket_id, courier_pubkey, payment_buls)}


@BLUEPRINT.route("/v{}/refund_package".format(VERSION), methods=['POST'])
@swag_from("{}/refund_package.yml".format(SWAGGER_DIR))
@api.validation.call(['paket_id', 'refund_transaction'], require_auth=True)
# pylint: disable=unused-argument
# user_pubkey is used in decorator.
def refund_package_handler(user_pubkey, paket_id, refund_transaction):
    # pylint: enable=unused-argument
    return {'status': 200, 'transaction': paket.refund(paket_id, refund_transaction)}


# pylint: disable=unused-argument
# This function does not yet implement the filters.
@BLUEPRINT.route("/v{}/my_packages".format(VERSION), methods=['GET'])
@swag_from("{}/my_packages.yml".format(SWAGGER_DIR))
@api.validation.call(require_auth=True)
def my_packages_handler(user_pubkey, show_inactive=False, from_date=None, role_in_delivery=None):
    return {'status': 200, 'packages': db.get_packages()}
# pylint: enable=unused-argument


@BLUEPRINT.route("/v{}/package".format(VERSION), methods=['GET'])
@swag_from("{}/package.yml".format(SWAGGER_DIR))
@api.validation.call(['paket_id'])
def package_handler(paket_id):
    return {'status': 200, 'package': db.get_package(paket_id)}


# User routes.


@BLUEPRINT.route("/v{}/register_user".format(VERSION), methods=['POST'])
@swag_from("{}/register_user.yml".format(SWAGGER_DIR))
@api.validation.call(['full_name', 'phone_number', 'paket_user'], require_auth=True)
# Note that pubkey is different from user_pubkey in that it does not yet exist in the system.
def register_user_handler(pubkey, full_name, phone_number, paket_user):
    try:
        paket.stellar_base.keypair.Keypair.from_address(str(pubkey))
        db.create_user(pubkey, paket_user)

    # For debug purposes, we generate a pubkey if no valid key is found.
    except paket.stellar_base.utils.DecodeError:
        if not api.validation.DEBUG:
            raise
        keypair = paket.get_keypair()
        pubkey, seed = keypair.address().decode(), keypair.seed().decode()
        db.create_user(pubkey, paket_user, seed)
        paket.new_account(pubkey)
        paket.trust(keypair)

    return {'status': 201, 'user_details': db.update_user_details(pubkey, full_name, phone_number)}


@BLUEPRINT.route("/v{}/recover_user".format(VERSION), methods=['POST'])
@swag_from("{}/recover_user.yml".format(SWAGGER_DIR))
@api.validation.call(require_auth=True)
def recover_user_handler(user_pubkey):
    return {'status': 200, 'user_details': db.get_user(user_pubkey)}


# Debug routes.


@BLUEPRINT.route("/v{}/debug/users".format(VERSION), methods=['GET'])
@swag_from("{}/users.yml".format(SWAGGER_DIR))
@api.validation.call
def users_handler():
    return {'status': 200, 'users': {
        pubkey: dict(user, bul_account=paket.get_bul_account(pubkey)) for pubkey, user in db.get_users().items()}}


@BLUEPRINT.route("/v{}/debug/packages".format(VERSION), methods=['GET'])
@swag_from("{}/packages.yml".format(SWAGGER_DIR))
@api.validation.call
def packages_handler():
    return {'status': 200, 'packages': db.get_packages()}
