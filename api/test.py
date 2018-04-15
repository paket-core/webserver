"""Test the PaKeT API."""
import os
import unittest

import api.server
import api.routes
import db

db.DB_NAME = 'test.db'


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

    # pylint: disable=no-self-use
    def test_fresh_db(self):
        """Make sure packages table exists and is empty."""
        self.assertFalse(db.get_packages(), "Fresh DB should have no packages")

    # pylint: enable=no-self-use

    def test_register(self):
        """Register a new user."""
        response = self.app.post("/v{}/register_user".format(api.routes.VERSION), data={
            'paket_user': 'stam'
        })

        self.assertEqual(response.status_code, 400, "missing Params")
        response = self.app.post("/v{}/register_user".format(api.routes.VERSION),
                                 data={'paket_user': 'stam', 'phone_number': '123', 'full_name': 'first last'},
                                 headers={'Pubkey': 'replace with good key', 'Signature': 'sig', 'Footprint': 'foot'}
                                 )

        self.assertEqual(response.status_code, 404, "TODO")

