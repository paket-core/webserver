"""Validations for API calls."""
import contextlib
import functools
import logging
import os
import sqlite3

import flask

DEBUG = bool(os.environ.get('PAKET_DEBUG'))
LOGGER = logging.getLogger('pkt.api.validation')


class MissingFields(Exception):
    """Missing field in args."""


class InvalidField(Exception):
    """Invalid field."""


class FingerprintMismatch(Exception):
    """Fingerprint does not match call."""


class InvalidSignature(Exception):
    """Invalid signature."""


@contextlib.contextmanager
def sql_connection():
    """Context manager for querying the database."""
    try:
        connection = sqlite3.connect(DB_NAME)
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
            raise InvalidNonce("nonce {} is not an integer".format(new_nonce))
        sql.execute("UPDATE nonces SET nonce = ? WHERE pubkey = ?", (new_nonce, pubkey))
        if user_name:
            sql.execute("UPDATE nonces SET user_name = ? WHERE pubkey = ?", (user_name, pubkey))


def get_pubkey_from_user_name(user_name):
    """
    Get the pubkey associated with a user_name. Raise exception if user_name is unknown.
    For debug only.
    """
    LOGGER.warning("getting key for %s", user_name)
    with sql_connection() as sql:
        sql.execute('SELECT pubkey FROM nonces WHERE user_name = ?', (user_name,))
        try:
            return sql.fetchone()[0]
        except TypeError:
            raise UnknownUser("unknown user {}".format(user_name))

def check_missing_fields(fields, required_fields):
    """Raise exception if there are missing fields."""
    if required_fields is None:
        required_fields = set()
    missing_fields = set(required_fields) - set(fields)
    if missing_fields:
        raise MissingFields("Request does not contain field(s): {}".format(', '.join(missing_fields)))


def check_signature(user_pubkey, fingerprint, signature):
    """
    Raise exception on invalid signature.
    """
    LOGGER.ERROR("can't check signature for %s on %s (%s)", user_pubkey, fingerprint, signature)
    raise NotImplementedError('Signature checking is not yet implemented.')


def check_fingerprint(fingerprint, url, kwargs):
    """
    Raise exception on invalid fingerprint.
    """
    # Copy kwargs before we destroy it.
    kwargs = dict(kwargs)
    fingerprint = fingerprint.split(',')
    if url != fingerprint[0]:
        raise FingerprintMismatch("fingerprint {} does not match call to {}".format(fingerprint[0], url))
    try:
        update_nonce(kwargs['user_pubkey'], fingerprint[-1])
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


def check_and_fix_values(kwargs):
    """
    Raise exception for invalid values.
    "_buls" and "_timestamp" fields must be valid integers.
    "_pubkey" fields must be valid addresses (or user_name in debug mode).
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
            if DEBUG and value == 'debug':
                continue
            try:
                paket.stellar_base.keypair.Keypair.from_address(value)
            except (TypeError, paket.stellar_base.utils.DecodeError):
                if DEBUG:
                    if value is None:
                        continue
                    LOGGER.warning("Attempting conversion of %s %s to pubkey", key, value)
                    kwargs[key] = get_pubkey_from_user_name(value)
                else:
                    raise InvalidField("the value of {}({}) is not a valid public key".format(key, value))
    return kwargs


def check_and_fix_call(request, required_fields, require_auth):
    """Check call and extract kwargs."""
    kwargs = request.values.to_dict()
    check_missing_fields(kwargs.keys(), required_fields)

    if not DEBUG:
        if '/debug/' in request.path:
            raise FingerprintMismatch("{} only accesible in debug mode".format(request.path))

        if require_auth:
            check_missing_fields(request.headers.keys(), ['Pubkey', 'Fingerprint', 'Signature'])
            check_signature(request.headers['pubkey'], request.headers['Fingerprint'], request.headers['Signature'])
            check_fingerprint(request.headers['Fingerprint'], request.url, kwargs)

    if 'Pubkey' in request.headers:
        kwargs['user_pubkey'] = request.headers['Pubkey']

        # Special case for registering users that do not yet exists.
        if '/register_user' in request.path:
            kwargs['pubkey'] = kwargs['user_pubkey']
            del kwargs['user_pubkey']

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
        except FingerprintMismatch as exception:
            response = {'status': 403, 'error': str(exception)}
        except (UnknownUser, UnknownPaket, paket.stellar_base.utils.AccountNotExistError) as exception:
            response = {'status': 404, 'error': str(exception)}
        except DuplicateUser as exception:
            response = {'status': 409, 'error': str(exception)}
        except NotImplementedError as exception:
            response = {'status': 501, 'error': str(exception)}
        except Exception as exception:
            LOGGER.exception("Unknown validation exception. Headers: %s", flask.request.headers)
            if DEBUG:
                response['debug'] = str(exception)
        if 'error' in response:
            LOGGER.error(response['error'])
        return flask.make_response(flask.jsonify(response), response.get('status', 200))
    return _call
