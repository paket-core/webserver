"""JSON swagger API to PaKeT."""
import logging

import flask
from flasgger import swag_from

import api.validation
import db
import paket

VERSION = '1'
LOGGER = logging.getLogger('pkt.api.routes')
BLUEPRINT = flask.Blueprint('api.routes', __name__)
SWAGGER_CONFIG = {
    'title': 'PaKeT API',
    'uiversion': 2,
    'specs_route': '/',
    'info': {
        'title': 'The PaKeT http server API',
        'description': """
Web API Server for The PaKeT Project

What is this?
=============
This page is used as both documentation of our server API and as a sandbox to
test interaction with it. You can use this page to call the RESTful API while
specifying any required or optional parameter. The page also presents curl
commands that can be used to call the server.

Our Server
==========
We run a centralized server that can be used to interact with PaKeT's bottom
layers.  Since Layer one is completely implemented on top of the Stellar
network, it can be interacted with directly in a fully decentralized fashion.
We created this server only as a gateway to the bottom layers to simplify the interaction with them.

Another aspect of the server is to interact with our user information.
Ultimately, we will use decentralize user information solutions, such as Civic,
but right now we are keeping user for both KYC and app usage. Please review our
roadmap to see our plans for decentralizing the user data.

Security
========

Some explanation on keypairs and signatures and how to use them.

Walkthrough sample
==================

You can follow the following steps one by one.
They are ordered in a way that demonstrates the main functionality of the API.

Register a user
---------------

First, register a new user:
* register_user: if you are in debug mode make sure to use the value 'debug' as the Pubkey header. In such a case,
a keypair will be generated and held on your behalf by the system.
Your call should return with status code 201 and a JSON with the new user's details.
On the debug environment this will include the generated secret seed of the keypair.

* recover_user: use the pubkey from the previous step.
Your call should return with a status of 200 and all the details of the user
(including the secret seed on the debug environment, as above).

Funding with wallet functions
-----------------------------

Verify a zero balance, and than fund the account.
* get_bul_account: use the same pubkey as before.
Your call should return a status of 200 and include the newly created user's balance in BULs (should be 0),
a list of the signers on the account (should be only the user's pubkey),
a list of thresholds (should all be 0) and a sequence number (should be a large integer).

* send_buls: In a production environment, you should use the keypair of a BUL holding account you control for the
headers. On the debug environment, you should use the value 'ISSUER', which has access to an unlimited supply of BULs,
for the Pubkey header. Use the pubkey from before as value for the to_pubkey field, and send yourself 222 BULs.
Your call should return with a status of 201, and include the transaction details.
Of these, copy the value of ['transaction']['hash'] and use the form on the following page to fetch and examine it:
https://www.stellar.org/laboratory/#explorer?resource=transactions&endpoint=single&network=test

Specifically, if you click the envelope_xdr that you will receive it will open in the XDR viewer where you can
view the payment operation, and if you click the result_xdr you can check that the payment operation has succeeded.

* get_bul_account: use this call again, with the new user's pubkey,
to ensure that your balance reflects the latest transaction.
Your call should return a status of 200 with the same details as the previous call,
excepting that the balance should now be 222.

Create a package
----------------

Create (launch) a new package.

* launch_package: use the new user's pubkey in the header.
Use the recipient's pubkey for the recipient_pubkey field and the courier's pubkey for the courier_pubkey field
(in the debug environment you can use the strings 'RECIPIENT' and 'COURIER' for the built-in pre-funded accounts).
Set the deadline for the delivery in Unix time (https://en.wikipedia.org/wiki/Unix_time),
with 22 BULs as payment_buls and 50 BULs as collateral_buls.

test in the future
==================

debug functions
price
prepare_send_buls
submit_transaction

The API
=======

""",
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


@BLUEPRINT.route("/v{}/submit_transaction".format(VERSION), methods=['POST'])
@swag_from("swagfiles/submit_transaction.yml")
@api.validation.call(['transaction'])
def submit_transaction_handler(user_pubkey, transaction):
    return {'status': 200, 'transaction': paket.submit_transaction_envelope(user_pubkey, transaction)}


@BLUEPRINT.route("/v{}/bul_account".format(VERSION), methods=['POST'])
@swag_from("swagfiles/bul_account.yml")
@api.validation.call
def bul_account_handler(user_pubkey):
    return dict(status=200, **paket.get_bul_account(user_pubkey))


@BLUEPRINT.route("/v{}/send_buls".format(VERSION), methods=['POST'])
@swag_from("swagfiles/send_buls.yml")
@api.validation.call(['to_pubkey', 'amount_buls'])
def send_buls_handler(user_pubkey, to_pubkey, amount_buls):
    return {'status': 201, 'transaction': paket.send_buls(user_pubkey, to_pubkey, amount_buls)}


@BLUEPRINT.route("/v{}/prepare_send_buls".format(VERSION), methods=['POST'])
@swag_from("swagfiles/prepare_send_buls.yml")
@api.validation.call(['to_pubkey', 'amount_buls'])
def prepare_send_buls_handler(user_pubkey, to_pubkey, amount_buls):
    return {'status': 200, 'transaction': paket.prepare_send_buls(user_pubkey, to_pubkey, amount_buls)}


@BLUEPRINT.route("/v{}/launch_package".format(VERSION), methods=['POST'])
@swag_from("swagfiles/launch_package.yml")
@api.validation.call(['recipient_pubkey', 'courier_pubkey', 'deadline_timestamp', 'payment_buls', 'collateral_buls'])
def launch_package_handler(
        user_pubkey, recipient_pubkey, courier_pubkey, deadline_timestamp, payment_buls, collateral_buls):
    escrow_address, refund_transaction, payment_transaction = paket.launch_paket(
        user_pubkey, recipient_pubkey, courier_pubkey, deadline_timestamp, payment_buls, collateral_buls
    )
    return {
        'status': 200, 'escrow_address': escrow_address,
        'refund_transaction': refund_transaction, 'payment_transaction': payment_transaction}


@BLUEPRINT.route("/v{}/accept_package".format(VERSION), methods=['POST'])
@swag_from("swagfiles/accept_package.yml")
@api.validation.call(['paket_id'])
def accept_package_handler(user_pubkey, paket_id, payment_transaction=None):
    paket.accept_package(user_pubkey, paket_id, payment_transaction)
    return {'status': 200}


@BLUEPRINT.route("/v{}/relay_package".format(VERSION), methods=['POST'])
@swag_from("swagfiles/relay_package.yml")
@api.validation.call(['paket_id', 'courier_pubkey', 'payment_buls'])
def relay_package_handler(user_pubkey, paket_id, courier_pubkey, payment_buls):
    return {'status': 200, 'transaction': paket.relay_payment(user_pubkey, paket_id, courier_pubkey, payment_buls)}


@BLUEPRINT.route("/v{}/refund_package".format(VERSION), methods=['POST'])
@swag_from("swagfiles/refund_package.yml")
@api.validation.call(['paket_id', 'refund_transaction'])
# pylint: disable=unused-argument
# user_pubkey is used in decorator.
def refund_package_handler(user_pubkey, paket_id, refund_transaction):
    # pylint: enable=unused-argument
    return {'status': 200, 'transaction': paket.refund(paket_id, refund_transaction)}


# pylint: disable=unused-argument
@BLUEPRINT.route("/v{}/my_packages".format(VERSION), methods=['POST'])
@swag_from("swagfiles/my_packages.yml")
@api.validation.call()
def my_packages_handler(user_pubkey, show_inactive=False, from_date=None, role_in_delivery=None):
    return {'status': 200, 'packages': db.get_packages()}
# pylint: disable=unused-argument


@BLUEPRINT.route("/v{}/package".format(VERSION), methods=['POST'])
@swag_from("swagfiles/package.yml")
@api.validation.call()
def package_handler(user_pubkey, paket_id):
    return {'status': 200, 'package': db.get_package(paket_id)}


@BLUEPRINT.route("/v{}/register_user".format(VERSION), methods=['POST'])
@swag_from("swagfiles/register_user.yml")
@api.validation.call(['full_name', 'phone_number', 'paket_user'])
def register_user_handler(user_pubkey, full_name, phone_number, paket_user):
    try:
        paket.stellar_base.keypair.Keypair.from_address(str(user_pubkey))
        db.create_user(user_pubkey, paket_user)

    # For debug purposes, we generate a pubkey if no valid key is found.
    except paket.stellar_base.utils.DecodeError:
        if not api.validation.DEBUG:
            raise
        keypair = paket.get_keypair()
        user_pubkey, seed = keypair.address().decode(), keypair.seed().decode()
        db.create_user(user_pubkey, paket_user, seed)
        paket.new_account(user_pubkey)
        paket.trust(keypair)

    return {'status': 201, 'user_details': db.update_user_details(user_pubkey, full_name, phone_number)}


@BLUEPRINT.route("/v{}/recover_user".format(VERSION), methods=['POST'])
@swag_from("swagfiles/recover_user.yml")
@api.validation.call
def recover_user_handler(user_pubkey):
    return {'status': 200, 'user_details': db.get_user(user_pubkey)}


@BLUEPRINT.route("/v{}/price".format(VERSION), methods=['POST'])
@swag_from("swagfiles/price.yml")
def price_handler():
    return flask.jsonify({'status': 200, 'buy_price': 1, 'sell_price': 1})


@BLUEPRINT.route("/v{}/debug/users".format(VERSION), methods=['GET'])
@swag_from("swagfiles/users.yml")
@api.validation.call
def users_handler():
    return {'status': 200, 'users': {
        pubkey: dict(user, bul_account=paket.get_bul_account(pubkey)) for pubkey, user in db.get_users().items()}}


@BLUEPRINT.route("/v{}/debug/packages".format(VERSION), methods=['GET'])
@swag_from("swagfiles/packages.yml")
@api.validation.call
def packages_handler():
    return {'status': 200, 'packages': db.get_packages()}
