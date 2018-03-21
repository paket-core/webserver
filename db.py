"""PaKeT database interface."""
import contextlib
import logging
import sqlite3

LOGGER = logging.getLogger('pkt.db')
DB_NAME = 'paket.db'


class UnknownUser(Exception):
    """Unknown user ID."""


class DuplicateUser(Exception):
    """Duplicate user."""


class InvalidNonce(Exception):
    """Invalid nonce."""


@contextlib.contextmanager
def sql_connection(db_name=DB_NAME):
    """Context manager for querying the database."""
    try:
        connection = sqlite3.connect(db_name)
        connection.row_factory = sqlite3.Row
        yield connection.cursor()
        connection.commit()
    except sqlite3.Error as db_exception:
        raise db_exception
    finally:
        if 'connection' in locals():
            # noinspection PyUnboundLocalVariable
            connection.close()


def init_db():
    """Initialize the database."""
    with sql_connection() as sql:
        # Not using IF EXISTS here in case we want different handling.
        sql.execute('SELECT name FROM sqlite_master WHERE type = "table" AND name = "users"')
        if len(sql.fetchall()) == 1:
            LOGGER.debug('database already exists')
            return
        sql.execute('''
            CREATE TABLE users(
                address VARCHAR(42) PRIMARY KEY,
                full_name VARCHAR(256),
                phone_number VARCHAR(32),
                paket_user VARCHAR(32) UNIQUE)''')
        LOGGER.debug('users table created')
        sql.execute('''
            CREATE TABLE packages(
                paket_id VARCHAR(1024) UNIQUE,
                launcher_address VARCHAR(42),
                recipient_address VARCHAR(42),
                custodian_address VARCHAR(42),
                payment INTEGER,
                collateral INTEGER,
                kwargs VARCHAR(1024))''')
        LOGGER.debug('packages table created')
        sql.execute('''
            CREATE TABLE nonces(
                address VARCHAR(42) PRIMARY KEY,
                nonce INTEGER NOT NULL DEFAULT 0)''')
        LOGGER.debug('nonces table created')


def create_user(address):
    """Create a new user."""
    with sql_connection() as sql:
        try:
            sql.execute("INSERT INTO users (address) VALUES (?)", (address,))
            sql.execute("INSERT INTO nonces (address) VALUES (?)", (address,))
        except sqlite3.IntegrityError:
            raise DuplicateUser("Address {} is non unique".format(address))


def get_user(address):
    """Get user details."""
    with sql_connection() as sql:
        sql.execute("SELECT * FROM users WHERE address = ?", (address,))
        user = sql.fetchone()
        return {key: user[key] for key in user.keys()} if user else None


def update_user_details(address, full_name, phone_number, paket_user):
    """Update user details."""
    with sql_connection() as sql:
        try:
            sql.execute("""
                UPDATE users SET
                full_name = ?,
                phone_number = ?,
                paket_user = ?
                WHERE address = ?""", (full_name, phone_number, paket_user, address))
        except sqlite3.IntegrityError:
            raise DuplicateUser("paket_user {} is not unique".format(paket_user))
    return get_user(address)


def get_users():
    """Get list of users and addresses - for debug only."""
    with sql_connection() as sql:
        sql.execute('SELECT * FROM users')
        users = sql.fetchall()
    return {user['address']: {key: user[key] for key in user.keys() if key != 'address'} for user in users}


def get_user_address(paket_user):
    """
    Get the address associated with a paket_user. Raise exception if paket_user is unknown.
    For debug only.
    """
    with sql_connection() as sql:
        sql.execute('SELECT address FROM users WHERE paket_user = ?', (paket_user,))
        try:
            return sql.fetchone()[0]
        except TypeError:
            raise UnknownUser("Unknown user {}".format(paket_user))


def create_package(paket_id, launcher_address, recipient_address, payment, collateral):
    """Create a new package row."""
    with sql_connection() as sql:
        sql.execute("""
            INSERT INTO packages (
                paket_id, launcher_address, recipient_address, custodian_address, payment, collateral
            ) VALUES (?, ?, ?, ?, ?, ?)""", (
                str(paket_id), launcher_address, recipient_address, launcher_address, payment, collateral))


def get_package(paket_id):
    """Get package details."""
    with sql_connection() as sql:
        sql.execute("SELECT * FROM packages WHERE paket_id = ?", (paket_id,))
        package = sql.fetchone()
    return {key: package[key] for key in package.keys()}


def get_packages():
    """Get a list of packages."""
    with sql_connection() as sql:
        sql.execute('SELECT paket_id, launcher_address, custodian_address, recipient_address FROM packages')
        packages = sql.fetchall()
    return {package['paket_id']: {key: package[key] for key in package.keys()} for package in packages}


def update_custodian(paket_id, custodian_address):
    """Update a package's custodian."""
    with sql_connection() as sql:
        sql.execute("UPDATE packages SET custodian_address = ? WHERE paket_id = ?", (custodian_address, paket_id))


def update_nonce(address, new_nonce):
    """Update a user's nonce."""
    with sql_connection() as sql:
        sql.execute("SELECT nonce FROM nonces WHERE address = ?", (address,))
        try:
            if int(new_nonce) <= sql.fetchone()['nonce']:
                raise InvalidNonce("nonce {} is not bigger than current nonce".format(new_nonce))
        except TypeError:
            raise UnknownUser("{} has no current nonce".format(address))
        except ValueError:
            raise InvalidNonce("nonce {} is not an integer".format(new_nonce))
        sql.execute("UPDATE nonces SET nonce = ? WHERE address = ?", (new_nonce, address))
