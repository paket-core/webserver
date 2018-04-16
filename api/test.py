"""Test the PaKeT API."""
import os
import unittest

import api.server
import api.routes
import db
import paket

db.DB_NAME = 'test.db'


class MockPaket:
    """Mock paket package."""

    def __init__(self):
        self.balances = {}

    def __getattr__(self, name):
        """Inherit all paket attributes that are not overwritten."""
        return getattr(paket, name)

    def new_account(self, address):
        """Create a new account."""
        if address in self.balances:
            raise paket.StellarTransactionFailed
        self.balances[address] = 0

    def trust(self, keypair):
        """Trust an account."""
        if keypair.address().decode() not in self.balances:
            raise paket.StellarTransactionFailed


api.server.paket = api.routes.paket = MockPaket()


class TestAPI(unittest.TestCase):
    """Test our API."""

    def setUp(self):
        try:
            os.unlink(db.DB_NAME)
        except FileNotFoundError:
            pass
        api.server.APP.testing = True
        self.app = api.server.APP.test_client()
        with api.server.APP.app_context():
            db.init_db()

    def tearDown(self):
        os.unlink(db.DB_NAME)

    def test_fresh_db(self):
        """Make sure packages table exists and is empty."""
        self.assertEqual(db.get_packages(), [], 'packages found in empty db')
        self.assertEqual(db.get_users(), {}, 'users found in empty db')

    def test_register(self):
        """Register a new user."""
        response = self.app.post(
            "/v{}/register_user".format(api.routes.VERSION),
            data={
                'full_name': 'Full Name',
                'phone_number': '123',
                'paket_user': 'stam'},
            headers={
                'Pubkey': '',
                'Footprint': '',
                'Signature': ''
            })
        self.assertEqual(response.status_code, 201, 'user creation failed')
