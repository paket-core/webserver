"""A snippet from the PaKeT API tester."""
import json
import unittest

import api
import logger
import paket
import webserver.validation

webserver.validation.NONCES_DB_NAME = 'nonce_test.db'
LOGGER = logger.logging.getLogger('pkt.api.test')
logger.setup()
APP = webserver.setup(api.BLUEPRINT)
APP.testing = True


class TestAPI(unittest.TestCase):
    """Test our API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = APP.test_client()
        self.host = 'http://localhost'

    def call(self, path, expected_code=None, fail_message=None, seed=None, **kwargs):
        """Post data to API server."""
        LOGGER.info("calling %s", path)
        if seed:
            fingerprint = webserver.validation.generate_fingerprint(
                "{}/v{}/{}".format(self.host, api.VERSION, path), kwargs)
            signature = webserver.validation.sign_fingerprint(fingerprint, seed)
            headers = {
                'Pubkey': paket.get_keypair(seed=seed).address().decode(),
                'Fingerprint': fingerprint, 'Signature': signature}
        else:
            headers = None
        response = self.app.post("/v{}/{}".format(api.VERSION, path), headers=headers, data=kwargs)
        response = dict(real_status_code=response.status_code, **json.loads(response.data.decode()))
        if expected_code:
            self.assertEqual(response['real_status_code'], expected_code, "{} ({})".format(
                fail_message, response.get('error')))
        return response

    def submit(self, transaction, seed=None, error='error submitting transaction'):
        """Submit a transaction, optionally adding seed's signature."""
        if seed:
            builder = paket.stellar_base.builder.Builder(horizon=paket.HORIZON, secret=seed)
            builder.import_from_xdr(transaction)
            builder.sign()
            transaction = builder.gen_te().xdr().decode()
        return self.call('submit_transaction', 200, error, transaction=transaction)

    def send(self, from_seed, to_pubkey, amount_buls):
        """Send BULs between accounts."""
        from_pubkey = paket.get_keypair(seed=from_seed).address().decode()
        LOGGER.info("sending %s from %s to %s", amount_buls, from_pubkey, to_pubkey)
        unsigned = self.call(
            'prepare_send_buls', 200, "can not prepare send from {} to {}".format(from_pubkey, to_pubkey),
            from_pubkey=from_pubkey, to_pubkey=to_pubkey, amount_buls=amount_buls)['transaction']
        self.submit(unsigned, from_seed, 'failed submitting send transaction')
