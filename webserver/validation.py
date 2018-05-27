"""Validations for API calls."""
import base64
import contextlib
import functools
import logging
import os
import sqlite3
import time

import flask
import stellar_base.keypair
import stellar_base.utils

NONCES_DB_NAME = 'nonces.db'
DEBUG = bool(os.environ.get('PAKET_DEBUG'))
LOGGER = logging.getLogger('pkt.api.validation')


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


@contextlib.contextmanager
def sql_connection():
    """Context manager for querying the database."""
    try:
        connection = sqlite3.connect(NONCES_DB_NAME)
        connection.row_factory = sqlite3.Row
        yield connection.cursor()
        connection.commit()
    except sqlite3.Error as db_exception:
        raise db_exception
    finally:
        if 'connection' in locals():
            # noinspection PyUnboundLocalVariable
            connection.close()


def init_nonce_db():
    """Initialize the nonces database."""
    with sql_connection() as sql:
        # Not using IF EXISTS here in case we want different handling.
        sql.execute('SELECT name FROM sqlite_master WHERE type = "table" AND name = "nonces"')
        if len(sql.fetchall()) == 1:
            LOGGER.debug('database already exists')
            return
        sql.execute('''
            CREATE TABLE nonces(
                pubkey VARCHAR(42) PRIMARY KEY,
                user_name VARCHAR(32) UNIQUE,
                nonce INTEGER NOT NULL DEFAULT 0)''')
        LOGGER.debug('nonces table created')


def update_nonce(pubkey, new_nonce, user_name=None):
    """Update a user's nonce (or create it)."""
    with sql_connection() as sql:
        sql.execute("SELECT nonce FROM nonces WHERE pubkey = ?", (pubkey,))
        try:
            if int(new_nonce) <= sql.fetchone()['nonce']:
                raise InvalidNonce("nonce {} is not bigger than current nonce".format(new_nonce))
        except TypeError:
            sql.execute("INSERT INTO nonces (pubkey) VALUES (?)", (pubkey,))
        except ValueError:
            raise InvalidNonce("fingerprint does not end with an integer nonce ({})".format(new_nonce))
        sql.execute("UPDATE nonces SET nonce = ? WHERE pubkey = ?", (new_nonce, pubkey))
        if user_name:
            sql.execute("UPDATE nonces SET user_name = ? WHERE pubkey = ?", (user_name, pubkey))


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
    try:
        update_nonce(user_pubkey, fingerprint[-1])
    except InvalidNonce as exception:
        raise FingerprintMismatch(str(exception))
    for key, val in [keyval.split('=') for keyval in fingerprint[1:-1]]:
        try:
            call_val = str(kwargs.pop(key))
        except KeyError:
            raise FingerprintMismatch("fingerprint has extra value {} = {}".format(key, val))
        if call_val != val:
            raise FingerprintMismatch("fingerprint {} = {} does not match call {} = {}".format(key, val, key, call_val))
    if kwargs:
        raise FingerprintMismatch("fingerprint is missing a value for {}".format(', '.join((kwargs.keys()))))
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
    signature = base64.b64decode(signature)
    fingerprint = bytes(fingerprint, 'utf-8')
    # pylint: disable=broad-except
    # If anything fails, we want to raise our own exception.
    try:
        stellar_base.keypair.Keypair.from_address(user_pubkey).verify(fingerprint, signature)
    except Exception:
        raise InvalidSignature("Signature does not match pubkey {} and data {}".format(user_pubkey, fingerprint))
    # pylint: enable=broad-except


def check_and_fix_values(kwargs):
    """
    Raise exception for invalid values.
    "_buls", "_xlms",  "_timestamp", and "_number" fields must be valid integers.
    "_pubkey" fields must be valid addresses.
    """
    for key, value in kwargs.items():
        if key.endswith('_buls') or key.endswith('_xlms') or key.endswith('_timestamp') or key.endswith('_num'):
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
                stellar_base.keypair.Keypair.from_address(value)
            except (TypeError, stellar_base.utils.DecodeError):
                if not DEBUG:
                    raise InvalidField("the value of {}({}) is not a valid public key".format(key, value))
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
            check_fingerprint(request.headers['pubkey'], request.headers['Fingerprint'], request.url, kwargs)
            check_signature(request.headers['pubkey'], request.headers['Fingerprint'], request.headers['Signature'])
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
        response = {'status': 500, 'error': 'Internal server error'}
        try:
            kwargs = check_and_fix_call(flask.request, required_fields, require_auth or False)
            response = handler(**kwargs)
        except (MissingFields, InvalidField) as exception:
            response = {'status': 400, 'error': str(exception)}
        except (FingerprintMismatch, InvalidSignature) as exception:
            response = {'status': 403, 'error': str(exception)}
        except UnknownUser as exception:
            response = {'status': 404, 'error': str(exception)}
        except AssertionError as exception:
            response = {'status': 409, 'error': str(exception)}
        except NotImplementedError as exception:
            response = {'status': 501, 'error': str(exception)}
        except Exception as exception:
            LOGGER.exception("Unknown validation exception. Headers: %s", flask.request.headers)
            if DEBUG:
                response['debug'] = str(exception)
        # pylint: enable=broad-except
        if 'error' in response:
            LOGGER.error(response['error'])
        return flask.make_response(flask.jsonify(response), response.get('status', 200))
    return _call
