"""Validations for API calls."""
import base64
import functools
import logging
import os
import time

import flask
import stellar_base.keypair
import stellar_base.utils

import util.db

NONCES_DB_NAME = 'nonces'
DEBUG = bool(os.environ.get('PAKET_DEBUG'))
LOGGER = logging.getLogger('pkt.api.validation')
KWARGS_CHECKERS_AND_FIXERS = {}
CUSTOM_EXCEPTION_STATUSES = {}
SQL_CONNECTION = util.db.custom_sql_connection('localhost', 3306, 'root', 'pass', NONCES_DB_NAME)


class MissingFields(Exception):
    """Missing field in args."""


class InvalidField(Exception):
    """Invalid field."""


class FingerprintMismatch(Exception):
    """Fingerprint does not match call."""


class InvalidNonce(Exception):
    """Invalid nonce."""


class InvalidSignature(Exception):
    """Invalid signature."""


class UnknownUser(Exception):
    """Unknown user."""


def init_nonce_db():
    """Initialize the nonces database."""
    with SQL_CONNECTION() as sql:
        # Not using IF EXISTS here in case we want different handling.
        sql.execute("SELECT table_name FROM information_schema.tables where table_name = 'nonces'")
        if len(sql.fetchall()) == 1:
            LOGGER.debug('database already exists')
            return
        sql.execute('''
            CREATE TABLE nonces(
                pubkey VARCHAR(56) PRIMARY KEY,
                user_name VARCHAR(32) UNIQUE,
                nonce INTEGER NOT NULL DEFAULT 0)''')
        LOGGER.debug('nonces table created')


def update_nonce(pubkey, new_nonce, user_name=None):
    """Update a user's nonce (or create it)."""
    with SQL_CONNECTION() as sql:
        sql.execute("SELECT nonce FROM nonces WHERE pubkey = %s", (pubkey,))
        try:
            if int(new_nonce) <= sql.fetchone()['nonce']:
                raise InvalidNonce("nonce {} is not bigger than current nonce".format(new_nonce))
        except TypeError:
            sql.execute("INSERT INTO nonces (pubkey) VALUES (%s)", (pubkey,))
        except ValueError:
            raise InvalidNonce("fingerprint does not end with an integer nonce ({})".format(new_nonce))
        sql.execute("UPDATE nonces SET nonce = %s WHERE pubkey = %s", (new_nonce, pubkey))
        if user_name:
            sql.execute("UPDATE nonces SET user_name = %s WHERE pubkey = %s", (user_name, pubkey))


def check_missing_fields(fields, required_fields):
    """Raise exception if there are missing fields."""
    if required_fields is None:
        required_fields = set()
    missing_fields = set(required_fields) - set(fields)
    if missing_fields:
        raise MissingFields("Request does not contain field(s): {}".format(', '.join(missing_fields)))


def generate_fingerprint(uri, kwargs=None):
    """Helper function creating fingerprints for debug purposes."""
    kwargstring = ','.join([''] + ["{}={}".format(key, val) for key, val in kwargs.items()]) if kwargs else ''
    return "{}{},{}".format(uri, kwargstring, int(time.time() * 1000.0))


def check_fingerprint(user_pubkey, fingerprint, url, kwargs):
    """
    Raise exception on invalid fingerprint.
    """
    # Copy kwargs before we destroy it.
    kwargs = dict(kwargs)
    fingerprint = fingerprint.split(',')
    if url != fingerprint[0]:
        raise FingerprintMismatch("fingerprint {} does not match call to {}".format(fingerprint[0], url))
    for key, val in [keyval.split('=') for keyval in fingerprint[1:-1]]:
        try:
            call_val = str(kwargs.pop(key))
        except KeyError:
            raise FingerprintMismatch("fingerprint has extra value {} = {}".format(key, val))
        if call_val != val:
            raise FingerprintMismatch("fingerprint {} = {} does not match call {} = {}".format(key, val, key, call_val))
    if kwargs:
        raise FingerprintMismatch("fingerprint is missing a value for {}".format(', '.join((kwargs.keys()))))
    try:
        update_nonce(user_pubkey, fingerprint[-1])
    except InvalidNonce as exception:
        raise FingerprintMismatch(str(exception))
    return


def sign_fingerprint(fingerprint, seed):
    """Helper signing function for debug purposes."""
    fingerprint = bytes(fingerprint, 'utf-8')
    signature = stellar_base.keypair.Keypair.from_seed(seed).sign(fingerprint)
    return base64.b64encode(signature).decode()


def check_signature(user_pubkey, fingerprint, signature):
    """
    Raise exception on invalid signature.
    """
    try:
        signature = base64.b64decode(signature)
    except base64.binascii.Error:
        raise InvalidSignature('Signature is not base64 encoded')
    fingerprint = bytes(fingerprint, 'utf-8')
    # pylint: disable=broad-except
    # If anything fails, we want to raise our own exception.
    try:
        stellar_base.keypair.Keypair.from_address(user_pubkey).verify(fingerprint, signature)
    except Exception:
        raise InvalidSignature("Signature does not match pubkey {} and data {}".format(user_pubkey, fingerprint))
    # pylint: enable=broad-except


def check_and_fix_natural(key, value):
    """Raise exception if value is not an integer larger than zero."""
    try:
        # Cast to str before casting to int to make sure floats fail.
        int_val = int(str(value))
    except ValueError:
        raise InvalidField("the value of {}({}) is not an integer".format(key, value))
    if int_val < 0:
        raise InvalidField("the value of {}({}) is less than zero".format(key, value))
    return int_val


KWARGS_CHECKERS_AND_FIXERS['_nat'] = check_and_fix_natural


def check_pubkey(key, value):
    """Raise exception if value is not a valid pubkey."""
    try:
        stellar_base.keypair.Keypair.from_address(value)
    except (TypeError, stellar_base.utils.DecodeError):
        warning = "the value of {}({}) is not a valid public key".format(key, value)
        if DEBUG:
            LOGGER.warning(warning)
        else:
            raise InvalidField(warning)
    return value


KWARGS_CHECKERS_AND_FIXERS['_pubkey'] = check_pubkey


def check_and_fix_values(kwargs):
    """
    Run kwargs through appropriate checkers and fixers.
    """
    for key, value in kwargs.items():
        for suffix in KWARGS_CHECKERS_AND_FIXERS:
            if key.endswith(suffix):
                kwargs[key] = KWARGS_CHECKERS_AND_FIXERS[suffix](key, value)
    return kwargs


def check_and_fix_call(request, required_fields, require_auth):
    """Extract kwargs and validate call."""
    if not DEBUG and '/debug/' in request.path:
        raise FingerprintMismatch("{} only accesible in debug mode".format(request.path))
    kwargs = request.values.to_dict()
    check_missing_fields(kwargs.keys(), required_fields)
    if require_auth:
        check_missing_fields(request.headers.keys(), ['Pubkey'])
        if not DEBUG:
            check_missing_fields(request.headers.keys(), ['Fingerprint', 'Signature'])
            check_signature(request.headers['pubkey'], request.headers['Fingerprint'], request.headers['Signature'])
            check_fingerprint(request.headers['pubkey'], request.headers['Fingerprint'], request.url, kwargs)
        kwargs['user_pubkey'] = request.headers['Pubkey']
    return check_and_fix_values(kwargs)


def optional_arg_decorator(decorator):
    """A decorator for decorators than can accept optional arguments."""
    @functools.wraps(decorator)
    def wrapped_decorator(*args, **kwargs):
        """A wrapper to return a filled up function in case arguments are given."""
        if len(args) == 1 and not kwargs and callable(args[0]):
            return decorator(args[0])
        return lambda decoratee: decorator(decoratee, *args, **kwargs)
    return wrapped_decorator


CUSTOM_EXCEPTION_STATUSES[MissingFields] = 400
CUSTOM_EXCEPTION_STATUSES[InvalidField] = 400
CUSTOM_EXCEPTION_STATUSES[AssertionError] = 400
CUSTOM_EXCEPTION_STATUSES[FingerprintMismatch] = 403
CUSTOM_EXCEPTION_STATUSES[InvalidSignature] = 403
CUSTOM_EXCEPTION_STATUSES[UnknownUser] = 404
CUSTOM_EXCEPTION_STATUSES[NotImplementedError] = 501


# Since this is a decorator the handler argument will never be None, it is
# defined as such only to comply with python's syntactic sugar.
@optional_arg_decorator
def call(handler=None, required_fields=None, require_auth=None):
    """
    A decorator to handle all API calls: extracts arguments, validates them,
    fixes them, handles authentication, and then passes them to the handler,
    dealing with exceptions and returning a valid response.
    """
    @functools.wraps(handler)
    def _call(*_, **__):
        # pylint: disable=broad-except
        # If anything fails, we want to catch it here.
        try:
            kwargs = check_and_fix_call(flask.request, required_fields, require_auth or False)
            response = handler(**kwargs)
        except Exception as exception:
            response = {'status': CUSTOM_EXCEPTION_STATUSES.get(type(exception), 500)}
            if response['status'] == 500:
                LOGGER.exception("Unknown validation exception. Headers: %s", flask.request.headers)
                response['error'] = 'Internal server error'
                if DEBUG:
                    response['debug'] = str(exception)
            else:
                response['error'] = str(exception)
        # pylint: enable=broad-except
        if 'error' in response:
            LOGGER.error(response['error'])
        return flask.make_response(flask.jsonify(response), response.get('status', 200))
    return _call
