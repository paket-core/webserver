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
                pubkey VARCHAR(42) PRIMARY KEY,
                full_name VARCHAR(256),
                phone_number VARCHAR(32),
                paket_user VARCHAR(32) UNIQUE)''')
        LOGGER.debug('users table created')
        sql.execute('''
            CREATE TABLE packages(
                paket_id VARCHAR(1024) UNIQUE,
                launcher_pubkey VARCHAR(42),
                recipient_pubkey VARCHAR(42),
                custodian_pubkey VARCHAR(42),
                payment INTEGER,
                collateral INTEGER,
                kwargs VARCHAR(1024))''')
        LOGGER.debug('packages table created')
        sql.execute('''
            CREATE TABLE nonces(
                pubkey VARCHAR(42) PRIMARY KEY,
                nonce INTEGER NOT NULL DEFAULT 0)''')
        LOGGER.debug('nonces table created')


def create_user(pubkey):
    """Create a new user."""
    with sql_connection() as sql:
        try:
            sql.execute("INSERT INTO users (pubkey) VALUES (?)", (pubkey,))
            sql.execute("INSERT INTO nonces (pubkey) VALUES (?)", (pubkey,))
        except sqlite3.IntegrityError:
            raise DuplicateUser("Pubkey {} is non unique".format(pubkey))


def get_user(pubkey):
    """Get user details."""
    with sql_connection() as sql:
        sql.execute("SELECT * FROM users WHERE pubkey = ?", (pubkey,))
        user = sql.fetchone()
        return {key: user[key] for key in user.keys()} if user else None


def update_user_details(pubkey, full_name, phone_number, paket_user):
    """Update user details."""
    with sql_connection() as sql:
        try:
            sql.execute("""
                UPDATE users SET
                full_name = ?,
                phone_number = ?,
                paket_user = ?
                WHERE pubkey = ?""", (full_name, phone_number, paket_user, pubkey))
        except sqlite3.IntegrityError:
            raise DuplicateUser("paket_user {} is not unique".format(paket_user))
    return get_user(pubkey)


def get_users():
    """Get list of users and their details - for debug only."""
    with sql_connection() as sql:
        sql.execute('SELECT * FROM users')
        users = sql.fetchall()
    return {user['pubkey']: {key: user[key] for key in user.keys() if key != 'pubkey'} for user in users}


def get_pubkey_from_paket_user(paket_user):
    """
    Get the pubkey associated with a paket_user. Raise exception if paket_user is unknown.
    For debug only.
    """
    with sql_connection() as sql:
        sql.execute('SELECT pubkey FROM users WHERE paket_user = ?', (paket_user,))
        try:
            return sql.fetchone()[0]
        except TypeError:
            raise UnknownUser("Unknown user {}".format(paket_user))


def create_package(paket_id, launcher_pubkey, recipient_pubkey, payment, collateral):
    """Create a new package row."""
    with sql_connection() as sql:
        sql.execute("""
            INSERT INTO packages (
                paket_id, launcher_pubkey, recipient_pubkey, custodian_pubkey, payment, collateral
            ) VALUES (?, ?, ?, ?, ?, ?)""", (
                str(paket_id), launcher_pubkey, recipient_pubkey, launcher_pubkey, payment, collateral))


def get_package(paket_id):
    """Get package details."""
    with sql_connection() as sql:
        sql.execute("SELECT * FROM packages WHERE paket_id = ?", (paket_id,))
        package = sql.fetchone()
    return {key: package[key] for key in package.keys()}


def get_packages():
    """Get a list of packages."""
    with sql_connection() as sql:
        sql.execute('SELECT paket_id, launcher_pubkey, custodian_pubkey, recipient_pubkey FROM packages')
        return [dict(row) for row in sql.fetchall()]


def update_custodian(paket_id, custodian_pubkey):
    """Update a package's custodian."""
    with sql_connection() as sql:
        sql.execute("UPDATE packages SET custodian_pubkey = ? WHERE paket_id = ?", (custodian_pubkey, paket_id))


def update_nonce(pubkey, new_nonce):
    """Update a user's nonce."""
    with sql_connection() as sql:
        sql.execute("SELECT nonce FROM nonces WHERE pubkey = ?", (pubkey,))
        try:
            if int(new_nonce) <= sql.fetchone()['nonce']:
                raise InvalidNonce("nonce {} is not bigger than current nonce".format(new_nonce))
        except TypeError:
            raise UnknownUser("{} has no current nonce".format(pubkey))
        except ValueError:
            raise InvalidNonce("nonce {} is not an integer".format(new_nonce))
        sql.execute("UPDATE nonces SET nonce = ? WHERE pubkey = ?", (new_nonce, pubkey))
