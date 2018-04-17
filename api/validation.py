"""Validations for API calls."""
import functools
import os

import flask

import db
import paket
import logger

DEBUG = bool(os.environ.get('PAKET_DEBUG'))
LOGGER = logger.logging.getLogger('pkt.api.validation')


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


def check_footprint(footprint, url, kwargs):
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
        db.update_nonce(kwargs['user_pubkey'], footprint[-1])
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
    return


def check_signature(user_pubkey, footprint, signature):
    """
    Raise exception on invalid signature.
    """
    LOGGER.ERROR("can't check signature for %s on %s (%s)", user_pubkey, footprint, signature)
    raise NotImplementedError('Signature checking is not yet implemented.')


def check_and_fix_values(kwargs):
    """
    Raise exception for invalid values.
    "_buls" and "_timestamp" fields must be valid integers.
    "_pubkey" fields must be valid addresses (or paket_user in debug mode).
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
            except (TypeError, paket.stellar_base.utils.DecodeError):
                if DEBUG:
                    if value is None:
                        continue
                    LOGGER.warning("Attempting conversion of user ID %s to pubkey", value)
                    kwargs[key] = db.get_pubkey_from_paket_user(value)
                else:
                    raise InvalidField("the value of {}({}) is not a valid public key".format(key, value))
    return kwargs


def check_and_fix_call(request, required_fields):
    """Check call and extract kwargs."""
    kwargs = request.values.to_dict()
    check_missing_fields(kwargs.keys(), required_fields)
    if request.method == 'POST':
        check_missing_fields(request.headers.keys(), ['Pubkey', 'Footprint', 'Signature'])
    if not DEBUG:
        if '/debug/' in request.path:
            raise FootprintMismatch("{} only accesible in debug mode".format(request.path))
        check_footprint(request.headers['Footprint'], request.url, kwargs)
        check_signature(kwargs['pubkey'], request.headers['Footprint'], request.headers['Signature'])
    if DEBUG and '/register_user' in request.path:
        kwargs = check_and_fix_values(kwargs)
        kwargs['user_pubkey'] = None
    elif 'Pubkey' in request.headers:
        kwargs['user_pubkey'] = request.headers['Pubkey']
    kwargs = check_and_fix_values(kwargs)
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
def call(handler=None, required_fields=None):
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
    return _call
