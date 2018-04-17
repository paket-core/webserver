"""Test the PaKeT API."""
import json
import os
import unittest

import api.server
import api.routes
import db
import paket

USE_HORIZON = False
db.DB_NAME = 'test.db'


class MockPaket:
    """Mock paket package."""

    def __init__(self):
        self.balances = {}

    def __getattr__(self, name):
        """Inherit all paket attributes that are not overwritten."""
        return getattr(paket, name)

    def new_account(self, pubkey):
        """Create a new account."""
        if pubkey in self.balances:
            raise paket.StellarTransactionFailed('account exists')
        self.balances[pubkey] = 0.0

    def trust(self, keypair):
        """Trust an account."""
        if keypair.address().decode() not in self.balances:
            raise paket.StellarTransactionFailed('account does not exists')

    def get_bul_account(self, pubkey):
        """Get account details of pubkey."""
        return {'balance': self.balances[pubkey]}

    def send_buls(self, from_pubkey, to_pubkey, amount):
        """Get account details of pubkey."""
        if from_pubkey != paket.ISSUER.address().decode():
            if self.balances[from_pubkey] < amount:
                raise paket.StellarTransactionFailed('insufficient funds')
            self.balances[from_pubkey] -= amount
        self.balances[to_pubkey] += amount


if not USE_HORIZON:
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

    def post(self, path, pubkey='', **kwargs):
        """Post data to API server."""
        response = self.app.post("/v{}/{}".format(api.routes.VERSION, path), headers={
            'Pubkey': pubkey,
            'Footprint': '',
            'Signature': ''
        }, data=kwargs)
        return response.status_code, json.loads(response.data.decode())

    def test_fresh_db(self):
        """Make sure packages table exists and is empty."""
        self.assertEqual(db.get_packages(), [], 'packages found in empty db')
        self.assertEqual(db.get_users(), {}, 'users found in empty db')

    def test_register(self):
        """Register a new user and recover it."""
        phone_number = str(os.urandom(8))
        self.assertEqual(self.post(
            'register_user',
            full_name='First Last',
            phone_number=phone_number,
            paket_user='stam'
        )[0], 201, 'user creation failed')
        self.assertEqual(
            self.post('recover_user', 'stam')[1]['user_details']['phone_number'],
            phone_number, 'user phone_number does not match')

    def test_send_buls(self):
        """Send BULs and check balance."""
        api.server.init_sandbox(True, False, False)
        self.post('register_user', full_name='First Last', phone_number='123', paket_user='stam')
        start_balance = self.post('bul_account', 'stam')[1]['balance']
        amount = 123
        self.post('send_buls', 'ISSUER', to_pubkey='stam', amount_buls=amount)
        end_balance = self.post('bul_account', 'stam')[1]['balance']
        self.assertEqual(end_balance - start_balance, amount, 'balance does not add up after send')
