"""JSON swagger API to PaKeT."""
import logging

import flask

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
@api.validation.call(['transaction'])
def submit_transaction_handler(user_pubkey, transaction):
    """
    Submit a signed transaction.
    Use this call to submit a signed transaction.
    A signed transaction is returned from /prepare_send_buls function.
    ---
    tags:
    - wallet
    parameters:
      - name: Pubkey
        in: header
        default: COURIER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/balance,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: transaction
        in: formData
        description: Transaction to submit
        required: true
        type: string
        default: 0
    responses:
      200:
        description: success
    """
    return {'status': 200, 'transaction': paket.submit_transaction_envelope(user_pubkey, transaction)}


@BLUEPRINT.route("/v{}/bul_account".format(VERSION), methods=['POST'])
@api.validation.call
def bul_account_handler(user_pubkey):
    """
    Get the details of your BUL account
    Use this call to get the balance and details of your account.
    ---
    tags:
    - wallet
    parameters:
      - name: Pubkey
        in: header
        default: COURIER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/balance,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
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
    return dict(status=200, **paket.get_bul_account(user_pubkey))


@BLUEPRINT.route("/v{}/send_buls".format(VERSION), methods=['POST'])
@api.validation.call(['to_pubkey', 'amount_buls'])
def send_buls_handler(user_pubkey, to_pubkey, amount_buls):
    """
    Transfer BULs to another pubkey.
    Use this call to send part of your balance to another user.
    The to_pubkey can be either a user id, or a wallet pubkey.
    ---
    tags:
    - wallet
    parameters:
      - name: Pubkey
        in: header
        default: LAUNCHER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: to_pubkey
        in: formData
        default: COURIER
        description: target pubkey for transfer
        required: true
        type: string
      - name: amount_buls
        in: formData
        default: 111
        description: amount to transfer
        required: true
        type: integer
    responses:
      200:
        description: transfer request sent
    """
    return {'status': 201, 'transaction': paket.send_buls(user_pubkey, to_pubkey, amount_buls)}


@BLUEPRINT.route("/v{}/prepare_send_buls".format(VERSION), methods=['POST'])
@api.validation.call(['to_pubkey', 'amount_buls'])
def prepare_send_buls_handler(user_pubkey, to_pubkey, amount_buls):
    # pylint: disable=line-too-long
    """
    Transfer BULs to another pubkey.
    Use this call to prepare a transaction that sends part of your balance to another user. This function will return an unsigned transaction.
    You can use the [laboratory](https://www.stellar.org/laboratory/#txsigner?network=test) to sign the transaction with your private key.
    You can use the /recover_user call to find out your seed.
    Than, you can either submit the signed transaction in the laboratory,
    or use the /submit_transaction call to send the signed transaction for submission.

    The to_pubkey can be either a user id, or a wallet pubkey.
    ---
    tags:
    - wallet
    parameters:
      - name: Pubkey
        in: header
        default: LAUNCHER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/prepare_send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: to_pubkey
        in: formData
        default: COURIER
        description: target pubkey for transfer
        required: true
        type: string
      - name: amount_buls
        in: formData
        default: 111
        description: amount to transfer
        required: true
        type: integer
    responses:
      200:
        description: transfer request sent
    """
    # pylint: enable=line-too-long
    return {'status': 200, 'transaction': paket.prepare_send_buls(user_pubkey, to_pubkey, amount_buls)}


@BLUEPRINT.route("/v{}/launch_package".format(VERSION), methods=['POST'])
@api.validation.call(['recipient_pubkey', 'courier_pubkey', 'deadline_timestamp', 'payment_buls', 'collateral_buls'])
def launch_package_handler(
        user_pubkey, recipient_pubkey, courier_pubkey, deadline_timestamp, payment_buls, collateral_buls
):
    # pylint: disable=line-too-long
    """
    Launch a package.
    Use this call to create a new package for delivery.
    ---
    tags:
    - packages
    parameters:
      - name: Pubkey
        in: header
        default: LAUNCHER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/launch_package,recipient_pubkey=pubkey,deadline_timestamp=timestamp,courier_pubkey=pubkey,payment_buls=buls,collateral_buls=buls,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: recipient_pubkey
        in: formData
        default: RECIPIENT
        description: Recipient pubkey
        required: true
        type: string
      - name: courier_pubkey
        in: formData
        default: COURIER
        description: Courier pubkey (can be id for now)
        required: true
        type: string
      - name: deadline_timestamp
        in: formData
        default: 9999999999
        description: Deadline timestamp
        required: true
        type: integer
        example: 1520948634
      - name: payment_buls
        in: formData
        default: 10
        description: BULs promised as payment
        required: true
        type: integer
      - name: collateral_buls
        in: formData
        default: 100
        description: BULs required as collateral
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
    # pylint: enable=line-too-long
    escrow_address, refund_transaction, payment_transaction = paket.launch_paket(
        user_pubkey, recipient_pubkey, courier_pubkey, deadline_timestamp, payment_buls, collateral_buls
    )
    return {
        'status': 200, 'escrow_address': escrow_address,
        'refund_transaction': refund_transaction, 'payment_transaction': payment_transaction}


@BLUEPRINT.route("/v{}/accept_package".format(VERSION), methods=['POST'])
@api.validation.call(['paket_id'])
def accept_package_handler(user_pubkey, paket_id, payment_transaction=None):
    """
    Accept a package.
    If the package requires collateral, commit it.
    If user is the package's recipient, release all funds from the escrow.
    ---
    tags:
    - packages
    parameters:
      - name: Pubkey
        in: header
        default: COURIER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/accept_package,paket_id=id,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: paket_id
        in: formData
        description: PKT id
        required: true
        type: string
        default: 0
      - name: payment_transaction
        in: formData
        description: Payment transaction of a previously launched package, required only if confirming receipt
        required: false
        type: string
        default: 0
    responses:
      200:
        description: Package accept requested
    """
    paket.accept_package(user_pubkey, paket_id, payment_transaction)
    return {'status': 200}


@BLUEPRINT.route("/v{}/relay_package".format(VERSION), methods=['POST'])
@api.validation.call(['paket_id', 'courier_pubkey', 'payment_buls'])
def relay_package_handler(user_pubkey, paket_id, courier_pubkey, payment_buls):
    # pylint: disable=line-too-long
    """
    Relay a package to another courier, offering payment.
    ---
    tags:
    - packages
    parameters:
      - name: Pubkey
        in: header
        default: COURIER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/relay_package,paket_id=id,courier_pubkey=pubkey,payment_buls=buls,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: paket_id
        in: formData
        description: PKT id
        required: true
        type: string
        default: 0
      - name: courier_pubkey
        in: formData
        default: NEWGUY
        description: Courier pubkey
        required: true
        type: string
      - name: payment_buls
        in: formData
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
    # pylint: enable=line-too-long
    return {'status': 200, 'transaction': paket.relay_payment(user_pubkey, paket_id, courier_pubkey, payment_buls)}


@BLUEPRINT.route("/v{}/refund_package".format(VERSION), methods=['POST'])
@api.validation.call(['paket_id', 'refund_transaction'])
# pylint: disable=unused-argument
# user_pubkey is used in decorator.
def refund_package_handler(user_pubkey, paket_id, refund_transaction):
    # pylint: enable=unused-argument
    # pylint: disable=line-too-long
    """
    Relay a package to another courier, offering payment.
    ---
    tags:
    - packages
    parameters:
      - name: Pubkey
        in: header
        default: COURIER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/refund_package,paket_id=id,refund_transaction=transaction,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: paket_id
        in: formData
        description: PKT id
        required: true
        type: string
        default: 0
      - name: refund_transaction
        in: formData
        description: Refund transaction of a previously launched package
        required: true
        type: string
        default: 0
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
    # pylint: enable=line-too-long
    return {'status': 200, 'transaction': paket.refund(paket_id, refund_transaction)}


# pylint: disable=unused-argument
@BLUEPRINT.route("/v{}/my_packages".format(VERSION), methods=['POST'])
@api.validation.call()
def my_packages_handler(user_pubkey, show_inactive=False, from_date=None, role_in_delivery=None):
    """
    Get list of packages
    Use this call to get a list of packages.
    You can filter the list by showing only active packages, or packages originating after a certain date.
    You can also filter to show only packages where the user has a specific role, such as "launcher" or "receiver".
    ---
    tags:
    - packages
    parameters:
      - name: Pubkey
        in: header
        default: COURIER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/my_packages,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: show_inactive
        in: formData
        description: include inactive packages in response
        required: false
        type: boolean
        default: false
      - name: from_date
        in: formData
        description: show only packages from this date forward
        required: false
        type: string
    responses:
      200:
        description: list of packages
        schema:
          properties:
            packages:
              type: array
              items:
                $ref: '#/definitions/Package-info'
          example:
            - PKT-id: 1001
              recipient-id: '@israel'
              custodian-id: '@moshe'
              my-role: 'receiver'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              payment: 120
              collateral: 400
              status: in transit
              blockchain-url: https://www.blockchain.info/423423423423424234534562
              paket-url: https://www.paket.global/paket-id/1001
              events:
                 - event-type: launch
                   paket_user: 'Lily'
                   GPS: '112341234.12341234123'
                   timestamp: 1231234
                 - event-type: give to carrier
                   paket_user: 'moshe'
                   GPS: '112341234.12341234123'
                   timestamp: 1231288
            - PKT-id: 1002
              recipient-id: '@Vowa'
              custodian-id: '@moshe'
              my-role: 'receiver'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              payment: 120
              collateral: 400
              status: in transit
              blockchain-url: https://www.blockchain.info/423423423423424234534562
              paket-url: https://www.paket.global/paket-id/1001
              events:
                 - event-type: launch
                   paket_user: 'Lulu'
                   GPS: '112341234.12341234123'
                   timestamp: 1231234
                 - event-type: give to carrier
                   paket_user: 'Lily'
                   GPS: '112341234.12341234123'
                   timestamp: 1231288
    """
    return {'status': 200, 'packages': db.get_packages()}
# pylint: disable=unused-argument


@BLUEPRINT.route("/v{}/package".format(VERSION), methods=['POST'])
@api.validation.call()
def package_handler(user_pubkey, paket_id):
    """
    Get a full info about a single package.
    ---
    tags:
    - packages
    parameters:
      - name: Pubkey
        in: header
        default: COURIER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/package,paket_id=id,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: paket_id
        in: formData
        description: PKT id
        required: true
        type: string
        default: 0
    definitions:
      Event:
        type: object
        properties:
          event-type:
            type: string
          timestamp:
            type: integer
          paket_user:
            type: string
          GPS:
            type: string
      Package-info:
        type: object
        properties:
          PKT-id:
            type: string
          blockchain-url:
            type: string
          collateral:
            type: integer
          custodian-id:
            type: string
          deadline-timestamp:
            type: integer
          my-role:
            type: string
          paket-url:
            type: string
          payment:
            type: integer
          recipient-id:
            type: string
          send-timestamp:
            type: integer
          status:
            type: string
          events:
            type: array
            items:
              $ref: '#/definitions/Event'
        example:
          PKT-id: 1001
          recipient-id: '@israel'
          custodian-id: '@moshe'
          my-role: 'receiver'
          send-timestamp: 41234123
          deadline-timestamp: 41244123
          payment: 120
          collateral: 400
          status: in transit
          blockchain-url: https://www.blockchain.info/423423423423424234534562
          paket-url: https://www.paket.global/paket-id/1001
          events:
             - event-type: launch
               paket_user: 'Lily'
               GPS: '112341234.12341234123'
               timestamp: 1231234
             - event-type: give to carrier
               paket_user: 'moshe'
               GPS: '112341234.12341234123'
               timestamp: 1231288
    responses:
      200:
        description: a single packages
        schema:
          $ref: '#/definitions/Package-info'
    """
    return {'status': 200, 'package': db.get_package(paket_id)}


@BLUEPRINT.route("/v{}/register_user".format(VERSION), methods=['POST'])
@api.validation.call(['full_name', 'phone_number', 'paket_user'])
def register_user_handler(user_pubkey, full_name, phone_number, paket_user):
    # pylint: disable=line-too-long
    """
    Register a new user.
    ---
    tags:
    - users
    parameters:
      - name: Pubkey
        default: debug
        in: header
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/register_user,full_name=name,phone_number=number,paket_user=user,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
      - name: paket_user
        in: formData
        description: User unique callsign
        required: true
        type: string
      - name: full_name
        in: formData
        default: First Last
        description: Full name of user
        required: true
        type: string
      - name: phone_number
        in: formData
        default: 123-456
        description: User phone number
        required: true
        type: string
    responses:
      201:
        description: user details registered.
    """
    # pylint: enable=line-too-long
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
@api.validation.call
def recover_user_handler(user_pubkey):
    """
    Recover user details.

    TODO about the seed
    ---
    tags:
    - users
    parameters:
      - name: Pubkey
        in: header
        default: COURIER
        schema:
            type: string
            format: string
      - name: Fingerprint
        in: header
        default: NOT NEEDED YET http://localhost:5000/v1/recover_user,1521650747
        schema:
            type: string
            format: string
      - name: Signature
        in: header
        default: NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc
        schema:
            type: string
            format: string
    responses:
      200:
        description: user details retrieved.
    """
    return {'status': 200, 'user_details': db.get_user(user_pubkey)}


@BLUEPRINT.route("/v{}/price".format(VERSION), methods=['POST'])
def price_handler():
    """
    Get buy and sell prices.
    ---
    tags:
    - wallet
    responses:
      200:
        description: buy and sell prices
        schema:
          properties:
            buy_price:
              type: integer
              format: int32
              minimum: 0
              description: price for which a BUL may me purchased
            sell_price:
              type: integer
              format: int32
              minimum: 0
              description: price for which a BUL may me sold
          example:
            {
                "status": 200,
                "buy_price": 1,
                "sell_price": 1
            }
    """
    return flask.jsonify({'status': 200, 'buy_price': 1, 'sell_price': 1})


@BLUEPRINT.route("/v{}/debug/users".format(VERSION), methods=['GET'])
@api.validation.call
def users_handler():
    """
    Get a list of users and their details - for debug only.
    ---
    tags:
    - debug
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
            "status": 200,
            "users": {
                "0x5E764542CC5CaB16e2a5440b60c43792a2703361": {
                "full_name": "courier",
                "paket_user": "courier",
                "phone_number": "123-456"
                },
                "0xC87CE45Af751367300bb8ea62B2f5442337211bE": {
                "full_name": "recipient",
                "paket_user": "recipient",
                "phone_number": "123-456"
                },
                "0xb91927C0F744aB701eb7dBF0bCF30a77F14c922C": {
                "full_name": "launcher",
                "paket_user": "launcher",
                "phone_number": "123-456"
                },
                "0xe77a8Ec88B5854B677C1B6Cc5447b199ACc1A94e": {
                "full_name": "owner",
                "paket_user": "owner",
                "phone_number": "123-456"
                }
            }
    """
    return {'status': 200, 'users': {
        pubkey: dict(user, bul_account=paket.get_bul_account(pubkey)) for pubkey, user in db.get_users().items()}}


@BLUEPRINT.route("/v{}/debug/packages".format(VERSION), methods=['GET'])
@api.validation.call
def packages_handler():
    """
    Get list of packages - for debug only.
    ---
    tags:
    - debug
    responses:
      200:
        description: list of packages
        schema:
          properties:
            packages:
              type: array
              items:
                $ref: '#/definitions/Package-info'
          example:
            - PKT-id: 1001
              recipient-id: '@israel'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              payment: 120
              collateral: 400
              status: in transit
              paket-url: https://www.paket.global/paket-id/1001
              blockchain-url: https://www.blockchain.info/423423423423424234534562
            - PKT-id: 1002
              recipient-id: '@oren'
              send-timestamp: 41234123
              deadline-timestamp: 41244123
              payment: 20
              collateral: 40
              status: delivered
              paket-url: https://www.paket.global/paket-id/1002
              blockchain-url: https://www.blockchain.info/423423423423424234534562

    """
    return {'status': 200, 'packages': db.get_packages()}
