"""Web JSON swagger API to PaKeT smart contract."""
import functools
import os

import flasgger
import flask
import flask_limiter.util

import db
import paket
import logger

VERSION = '1'
DEBUG = bool(os.environ.get('PAKET_DEBUG'))
LOGGER = logger.logging.getLogger('pkt.api')
logger.setup()

# Initialize flask app.
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
        'title': 'The PaKeT http server API',
        'description': 'Web API Server for The PaKeT Project',
        'contact': {
            'name': 'Israel Levin',
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
flasgger.Swagger(APP)


class MissingFields(Exception):
    """Missing field in args."""


class InvalidField(Exception):
    """Invalid field."""


class FootprintMismatch(Exception):
    """Footprint does not match call."""


class InvalidSignature(Exception):
    """Invalid signature."""


def check_missing_fields(fields, required_fields):
    """Raise exception if there are missing fields."""
    if required_fields is None:
        required_fields = set()
    missing_fields = set(required_fields) - set(fields)
    if missing_fields:
        raise MissingFields(', '.join(missing_fields))


def check_and_fix_values(kwargs):
    """
    Raise exception for invalid values.
    "_buls" and "_timestamp" fields must be valid integers.
    "_pubkey" fields must be valid addresses.
    """
    for key, value in kwargs.items():
        if key.endswith('_buls') or key.endswith('_timestamp'):
            try:
                # Cast to str before casting to int to make sure floats fail.
                int_val = int(str(value))
            except ValueError:
                raise InvalidField("the value of {}({}) is not an integer".format(key, value))
            if int_val < 0:
                raise InvalidField("the value of {}({}) is less than zero".format(key, value))
            kwargs[key] = int_val
        elif key.endswith('_pubkey'):
            try:
                paket.stellar_base.keypair.Keypair.from_address(value)
            # For debug purposes, we allow user IDs as addresses.
            except paket.stellar_base.utils.DecodeError:
                LOGGER.exception("Attempting conversion of user ID %s to pubkey", value)
                kwargs[key] = db.get_pubkey_from_paket_user(value)
    return kwargs


def check_footprint(footprint, url, kwargs, user_pubkey):
    """
    Raise exception on invalid footprint.
    Currently does not do anything.
    """
    # Copy kwargs before we destroy it.
    kwargs = dict(kwargs)
    footprint = footprint.split(',')
    if url != footprint[0]:
        raise FootprintMismatch("footprint {} does not match call to {}".format(footprint[0], url))
    try:
        db.update_nonce(user_pubkey, footprint[-1])
    except db.InvalidNonce as exception:
        raise FootprintMismatch(str(exception))
    for key, val in [keyval.split('=') for keyval in footprint[1:-1]]:
        try:
            call_val = str(kwargs.pop(key))
        except KeyError:
            raise FootprintMismatch("footprint has extra value {} = {}".format(key, val))
        if call_val != val:
            raise FootprintMismatch("footprint {} = {} does not match call {} = {}".format(key, val, key, call_val))
    if kwargs:
        raise FootprintMismatch("footprint is missing a value for {}".format(', '.join((kwargs.keys()))))
    return footprint


def check_signature(url, kwargs, user_pubkey, footprint, signature):
    """
    Raise exception on invalid signature.
    Currently does not do anything.
    """
    if DEBUG:
        try:
            return db.get_pubkey_from_paket_user(user_pubkey)
        except db.UnknownUser:
            return None
    check_footprint(footprint, url, kwargs, user_pubkey)
    raise NotImplementedError('Signature checking is not yet implemented.', signature)
    #return pubkey


def check_and_fix_call(request, required_fields):
    """Check call and extract kwargs."""
    kwargs = request.values.to_dict()
    check_missing_fields(kwargs.keys(), required_fields)
    kwargs = check_and_fix_values(kwargs)
    kwargs['user_pubkey'] = check_signature(
        request.url, kwargs,
        request.headers.get('Pubkey'),
        request.headers.get('Footprint'),
        request.headers.get('Signature'))
    return kwargs


def optional_arg_decorator(decorator):
    """A decorator for decorators than can accept optional arguments."""
    @functools.wraps(decorator)
    def wrapped_decorator(*args, **kwargs):
        """A wrapper to return a filled up function in case arguments are given."""
        if len(args) == 1 and not kwargs and callable(args[0]):
            return decorator(args[0])
        return lambda decoratee: decorator(decoratee, *args, **kwargs)
    return wrapped_decorator


# Since this is a decorator the handler argument will never be None, it is
# defined as such only to comply with python's syntactic sugar.
@optional_arg_decorator
def api_call(handler=None, required_fields=None):
    """
    A decorator to handle all API calls: extracts arguments, validates them,
    fixes them, handles authentication, and then passes them to the handler,
    dealing with exceptions and returning a valid response.
    """
    @functools.wraps(handler)
    def _api_call(*_, **__):
        # pylint: disable=broad-except
        # If anything fails, we want to catch it here.
        response = {'status': 500, 'error': 'Internal server error'}
        try:
            kwargs = check_and_fix_call(flask.request, required_fields)
            response = handler(**kwargs)
        except MissingFields as exception:
            response = {'status': 400, 'error': "Request does not contain field(s): {}".format(exception)}
        except InvalidField as exception:
            response = {'status': 400, 'error': str(exception)}
        except FootprintMismatch as exception:
            response = {'status': 403, 'error': str(exception)}
        except (db.UnknownUser, db.UnknownPaket, paket.stellar_base.utils.AccountNotExistError) as exception:
            response = {'status': 404, 'error': str(exception)}
        except db.DuplicateUser as exception:
            response = {'status': 409, 'error': str(exception)}
        except NotImplementedError as exception:
            response = {'status': 501, 'error': str(exception)}
        except Exception as exception:
            LOGGER.exception("Unknown validation exception. Headers: %s", flask.request.headers)
            if DEBUG:
                response['debug'] = str(exception)
        if 'error' in response:
            LOGGER.warning(response['error'])
        return flask.make_response(flask.jsonify(response), response.get('status', 200))
    return _api_call


@APP.route("/v{}/balance".format(VERSION), methods=['POST'])
@api_call
def balance_handler(user_pubkey):
    """
    Get the balance of your account
    Use this call to get the balance of your account.
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
      - name: Footprint
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
    return {'available_buls': paket.get_bul_balance(user_pubkey)}


@APP.route("/v{}/send_buls".format(VERSION), methods=['POST'])
@api_call(['to_pubkey', 'amount_buls'])
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
      - name: Footprint
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
    return {'status': 200, 'promise': paket.send_buls(user_pubkey, to_pubkey, amount_buls)}


@APP.route("/v{}/launch_package".format(VERSION), methods=['POST'])
@api_call(['recipient_pubkey', 'courier_pubkey', 'deadline_timestamp', 'payment_buls', 'collateral_buls'])
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
      - name: Footprint
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
    escrow_address, refund_envelope, payment_envelope = paket.launch_paket(
        user_pubkey, recipient_pubkey, courier_pubkey, deadline_timestamp, payment_buls, collateral_buls
    )
    return {
        'status': 200, 'escrow_address': escrow_address, 'refund_envelope':
        refund_envelope, 'payment_envelope': payment_envelope}


@APP.route("/v{}/accept_package".format(VERSION), methods=['POST'])
@api_call(['paket_id'])
def accept_package_handler(user_pubkey, paket_id, payment_envelope=None):
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
      - name: Footprint
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
      - name: payment_envelope
        in: formData
        description: Payment envelope of a previously launched package, required only if confirming receipt
        required: false
        type: string
        default: 0
    responses:
      200:
        description: Package accept requested
    """
    paket.accept_package(user_pubkey, paket_id, payment_envelope)
    return {'status': 200}


@APP.route("/v{}/relay_package".format(VERSION), methods=['POST'])
@api_call(['paket_id', 'courier_pubkey', 'payment_buls'])
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
      - name: Footprint
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
    return {'status': 200, 'promise': paket.relay_payment(user_pubkey, paket_id, courier_pubkey, payment_buls)}


# pylint: disable=unused-argument
@APP.route("/v{}/my_packages".format(VERSION), methods=['POST'])
@api_call()
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
      - name: Footprint
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


@APP.route("/v{}/package".format(VERSION), methods=['POST'])
@api_call()
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
      - name: Footprint
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


@APP.route("/v{}/register_user".format(VERSION), methods=['POST'])
@api_call(['full_name', 'phone_number', 'paket_user'])
def register_user_handler(user_pubkey, full_name, phone_number, paket_user):
    # pylint: disable=line-too-long
    """
    Register a new user.
    ---
    tags:
    - users
    parameters:
      - name: Pubkey
        in: header
        schema:
            type: string
            format: string
      - name: Footprint
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
    # For debug purposes, we generate a pubkey if no valid key is found.
    except paket.stellar_base.utils.DecodeError:
        keypair = paket.get_keypair()
        user_pubkey, seed = keypair.address().decode(), keypair.seed().decode()
        paket.new_account(user_pubkey)
        paket.trust(keypair)
        db.create_user(user_pubkey, paket_user, seed)
    paket.new_account(user_pubkey)
    return {'status': 201, 'user_details': db.update_user_details(user_pubkey, full_name, phone_number)}


@APP.route("/v{}/recover_user".format(VERSION), methods=['POST'])
@api_call
def recover_user_handler(user_pubkey):
    """
    Recover user details.
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
      - name: Footprint
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


@APP.route("/v{}/price".format(VERSION), methods=['POST'])
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


@APP.route("/v{}/users".format(VERSION), methods=['GET'])
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
    return flask.jsonify({'status': 200, 'users': {
        pubkey: dict(user, balance=paket.get_bul_balance(pubkey)) for pubkey, user in db.get_users().items()}})


@APP.route("/v{}/packages".format(VERSION), methods=['GET'])
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
    return flask.jsonify({'status': 200, 'packages': db.get_packages()})


@APP.route('/')
@APP.route('/<path:path>', methods=['GET', 'POST'])
def catch_all_handler(path='index.html'):
    """All undefined endpoints try to serve from the static directories."""
    for directory in STATIC_DIRS:
        if os.path.isfile(os.path.join(directory, path)):
            return flask.send_from_directory(directory, path)
    return flask.jsonify({'status': 403, 'error': "Forbidden path: {}".format(path)}), 403


@APP.errorhandler(429)
def ratelimit_handler(error):
    """Custom error handler for rate limiting."""
    error = 'Rate limit ({}) exceeded'.format(error.description)
    LOGGER.warning(error)
    return flask.make_response(flask.jsonify({'status': 429, 'error': error}), 429)


def init_sandbox(fund=None):
    """Initialize database with debug values and fund users. For debug only."""
    db.init_db()

    for paket_user, seed in [
            (key.split('PAKET_USER_', 1)[1], value)
            for key, value in os.environ.items()
            if key.startswith('PAKET_USER_')
    ]:
        try:
            keypair = paket.get_keypair(seed)
            pubkey, seed = keypair.address().decode(), keypair.seed().decode()
            db.create_user(pubkey, paket_user, seed)
            db.update_user_details(pubkey, paket_user, '123-456')
            LOGGER.debug("Created user %s", paket_user)
        except db.DuplicateUser:
            LOGGER.debug("User %s already exists", paket_user)
            continue
        if not fund:
            continue
        try:
            paket.new_account(pubkey)
            paket.trust(keypair)
            balance = paket.get_bul_balance(pubkey)
            if balance and balance < 100:
                LOGGER.warning("user %s has only %s BUL", paket_user, balance)
                paket.send_buls(paket.ISSUER.address().decode(), pubkey, 1000 - balance)
        except paket.stellar_base.utils.AccountNotExistError:
            LOGGER.error("address %s does not exist", pubkey)
        except paket.StellarTransactionFailed:
            LOGGER.warning("address %s already exists", pubkey)
