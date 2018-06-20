"""Tests for webserver.validation module."""
import unittest
import time

import stellar_base.keypair
import util.logger

import webserver


LOGGER = util.logger.logging.getLogger('pkt.webserver.test')
util.logger.setup()


class TestCheckMissingFields(unittest.TestCase):
    """Tests for check_missing_fields function"""

    def test_sufficient_fields(self):
        """Test for sufficient fields"""
        data_set = [
            {'fields': ['key', 'value', 'repeat'], 'required_fields': None},
            {'fields': ['key', 'value', 'repeat'], 'required_fields': ['key', 'value']},
            {'fields': [], 'required_fields': None}
        ]
        for args in data_set:
            with self.subTest(**args):
                webserver.validation.check_missing_fields(**args)

    def test_missed_fields(self):
        """Test for missed fields"""
        fields = ['key', 'repeat']
        required_fields = ['key', 'value']
        self.assertRaises(webserver.validation.MissingFields, webserver.validation.check_missing_fields,
                          fields, required_fields)


class TestGenerateFingerprint(unittest.TestCase):
    """Tests for generate_fingerprint function"""

    def test_generate_fingerprint(self):
        """Test generating fingerprint"""
        data_set = [
            {
                'uri': '/v3/package',
                'kwargs': {'escrow_pubkey': stellar_base.keypair.Keypair.random().address().decode()},
            },
            {
                'uri': '/v3/my_packages',
                'kwargs': {},
            },
            {
                'uri': '/v3/prepare_trust',
                'kwargs': {
                    'from_pubkey': str(stellar_base.keypair.Keypair.random().address().decode()),
                    'limit': 1000}
            }
        ]
        for data in data_set:
            with self.subTest(**data):
                fingerprint = webserver.validation.generate_fingerprint(data['uri'], data['kwargs'])
                for key, value in data['kwargs'].items():
                    self.assertIn("{}={}".format(key, value), fingerprint)
                self.assertTrue(fingerprint.startswith(data['uri']))
                # checking fingerprint match format <uri>,[arg1=value1,[arg2=value2,...]]<timestamp>
                self.assertRegex(fingerprint, r'^(\/[\w]+)+,([\w]+=[\w]+,)*([0-9]{13})$')


class TestCheckFingerprint(unittest.TestCase):
    """Tests for check_fingerprint function"""

    def test_check_fingerprint(self):
        """Test the check_fingerprint function."""
        data_set = [
            {
                'user_pubkey': 'GD6ESJTJQUIR3LTSSCP3PHF6GDSXJPUQ6D3NJHJ73ZTWYZIRYFU6PQIH',
                'fingerprint': '/v3/accept_package,'
                               'escrow_pubkey=GAM7BELNXMX5I3CQRGQAFAYF73FMT7CV2RJHUPEYAIINT5YJ726UY2GG,'
                               "{:.0f}".format(time.time() * 1000),
                'url': '/v3/accept_package',
                'kwargs': {'escrow_pubkey': 'GAM7BELNXMX5I3CQRGQAFAYF73FMT7CV2RJHUPEYAIINT5YJ726UY2GG'}
            },
            {
                'user_pubkey': 'GBAVMZAX35P2S7L3ZVLX35GPFRQ5JYJTW5UYCH4GBW2RPSRWGAAOOPST',
                'fingerprint': '/v3/prepare_send_buls,'
                               'from_pubkey=GA6WNY4R4XS5EYKXXD2HLA7FICWOGFSFRUCPP7TPUSD4GVD2P4LABAUX,'
                               'to_pubkey=GB5JYX5SICATFI6JPXEI7MISKJZGEUGOVO4TKCF4N5UQCKZGOHMO5GGQ,amount_buls=10,'
                               "{:.0f}".format(time.time() * 1000),
                'url': '/v3/prepare_send_buls',
                'kwargs': {
                    'from_pubkey': 'GA6WNY4R4XS5EYKXXD2HLA7FICWOGFSFRUCPP7TPUSD4GVD2P4LABAUX',
                    'to_pubkey': 'GB5JYX5SICATFI6JPXEI7MISKJZGEUGOVO4TKCF4N5UQCKZGOHMO5GGQ',
                    'amount_buls': 10}
            },
            {
                'user_pubkey': 'GC47CNBNNNQKYXPKZ7B5Q2MLEVASYVLJINH2QSYZ7XW2TFOL4MFS7NT3',
                'fingerprint': '/v3/bul_account,'
                               'queried_pubkey=GAM7BELNXMX5I3CQRGQAFAYF73FMT7CV2RJHUPEYAIINT5YJ726UY2GG,'
                               "{:.0f}".format(time.time() * 1000),
                'url': '/v3/bul_account',
                'kwargs': {'queried_pubkey': 'GAM7BELNXMX5I3CQRGQAFAYF73FMT7CV2RJHUPEYAIINT5YJ726UY2GG'}
            }
        ]
        for data in data_set:
            with self.subTest(**data):
                webserver.validation.check_fingerprint(**data)

    def test_mismatch(self):
        """Test fingerprint mismatch."""
        data_set = [
            {
                'args': {
                    'user_pubkey': stellar_base.keypair.Keypair.random().address(),
                    'fingerprint': '/v3/some/uri,arg=qwerty,'
                                   "{:.0f}".format(time.time() * 1000),
                    'url': '/v3/another/uri',
                    'kwargs': {
                        'arg': 'qwerty'
                        }
                    },
                'exc_msg': 'fingerprint /v3/some/uri does not match call to /v3/another/uri'
            },
            {
                'args': {
                    'user_pubkey': stellar_base.keypair.Keypair.random().address(),
                    'fingerprint': '/v3/some/uri,arg=qwerty,onetwothree',
                    'url': '/v3/some/uri',
                    'kwargs': {
                        'arg': 'qwerty'
                    }
                },
                'exc_msg': 'fingerprint does not end with an integer nonce (onetwothree)'
            },
            {
                'args': {
                    'user_pubkey': stellar_base.keypair.Keypair.random().address(),
                    'fingerprint': '/v3/some/uri,arg=qwerty,another_arg=another_value,'
                                   "{:.0f}".format(time.time() * 1000),
                    'url': '/v3/some/uri',
                    'kwargs': {
                        'arg': 'qwerty'
                    }
                },
                'exc_msg': 'fingerprint has extra value another_arg = another_value'
            },
            {
                'args': {
                    'user_pubkey': stellar_base.keypair.Keypair.random().address(),
                    'fingerprint': '/v3/some/uri,arg=qwerty,another_arg=another_value,'
                                   "{:.0f}".format(time.time() * 1000),
                    'url': '/v3/some/uri',
                    'kwargs': {
                        'arg': 'qwerty',
                        'another_arg': 123
                    }
                },
                'exc_msg': 'fingerprint another_arg = another_value does not match call another_arg = 123'
            },
            {
                'args': {
                    'user_pubkey': stellar_base.keypair.Keypair.random().address(),
                    'fingerprint': '/v3/some/uri,arg=qwerty,'
                                   "{:.0f}".format(time.time() * 1000),
                    'url': '/v3/some/uri',
                    'kwargs': {
                        'arg': 'qwerty',
                        'another_arg': 123
                    }
                },
                'exc_msg': 'fingerprint is missing a value for another_arg'
            }
        ]
        for data in data_set:
            with self.subTest(**data), self.assertRaises(webserver.validation.FingerprintMismatch) as execution_context:
                webserver.validation.check_fingerprint(**data['args'])
            self.assertEqual(str(execution_context.exception), data['exc_msg'])

    def test_invalid_nonce(self):
        """Test invalid nonce."""
        user_pubkey = stellar_base.keypair.Keypair.random().address()
        escrow_pubkey = stellar_base.keypair.Keypair.random().address()
        fingerprint = "/v3/accept_package,escrow_pubkey={},{:.0f}".format(escrow_pubkey, 0)
        url = '/v3/accept_package'
        kwargs = {
            'escrow_pubkey': escrow_pubkey
        }
        webserver.validation.check_fingerprint(user_pubkey, fingerprint, url, kwargs)
        with self.assertRaises(webserver.validation.FingerprintMismatch) as execution_context:
            webserver.validation.check_fingerprint(user_pubkey, fingerprint, url, kwargs)
        self.assertTrue(str(execution_context.exception).endswith('is not bigger than current nonce'))


class TestSignFingerprint(unittest.TestCase):
    """Tests for sign_fingerprint function"""

    def test_sign(self):
        """Test signature generation."""
        fingerprint = '/some/uri,1528265594985'
        seed = 'SDZFK4IMXKBLCCGNWGFIVEPJLDAKMEL4MZBBMJ4P36UTCUOBX7T27WBG'
        signed = webserver.validation.sign_fingerprint(fingerprint, seed)
        self.assertEqual(signed,
                         'O25J3rMvvVQbent/+B+eb62+gEA4saB/zcUZblTL58CYx5akphMlKnJviUAJsy1fmkVgY+xdAV4AMAp4gSvuCA==')


class TestCheckSignature(unittest.TestCase):
    """Tests for check_signature function"""

    def test_check_signature(self):
        """Test signature checking."""
        pubkey = 'GAXPE5KLZEYRU2GPBQHS2HWNBG7I5EI7CSUP3DGDEZH7CJPYEM2I6ADQ'
        fingerprint = '/v3/some/uri,arg=qwerty,1528265594985'
        signature = 'GFQSrZc91ocbelD246doUpMkGbsTD8vO/hIV9P4oetHU4Kl4Xbb5AaEDarlHLYbxGKGl6cO6hriK+Zeox29pAg=='
        self.assertEqual(webserver.validation.check_signature(pubkey, fingerprint, signature), None)

    def test_check_invalid_signature(self):
        """Test invalid signature checking."""
        data_set = [
            {
                'user_pubkey': 'GDD3ZR6FA6TYUS3RW5CLCIKEKNGG6BOPTOTJN6V3IETGIEGWCMXGURBG',
                'fingerprint': "/v3/some/uri,arg=qwerty,{:.0f}".format(time.time() * 1000),
                'signature': 'GFQSrZc91ocbelD246doUpMkGbsTD8vO/hIV9P4oetHU4Kl4Xbb5AaEDarlHLYbxGKGl6cO6hriK+Zeox29pAg=='
            },
            {
                'user_pubkey': 'GAXPE5KLZEYRU2GPBQHS2HWNBG7I5EI7CSUP3DGDEZH7CJPYEM2I6ADQ',
                'fingerprint': "/v3/some/uri,arg=qwerty,{:.0f}".format(time.time() * 1000),
                'signature': 'GFQSrZc91ocbelD246doUpMkGbsTD8vO/hIV9P4oetHU4Kl4Xbb5AaEDarlHLYbxGKGl6cO6hriK+Zeox29pAg=='
            },
            {
                'user_pubkey': 'GAXPE5KLZEYRU2GPBQHS2HWNBG7I5EI7CSUP3DGDEZH7CJPYEM2I6ADQ',
                'fingerprint': "/v3/some/uri,arg=qwerty,{:.0f}".format(time.time() * 1000),
                'signature': 'GFDSrZc91ocbelo246doUpMkGbsTD8vO/hIV9P4oetHo4Kl4Xbb5AaEDarlHLYbxGKGl6cO6hriK+Zeox29pAg=='
            }
        ]
        for data in data_set:
            with self.subTest(**data), self.assertRaises(webserver.validation.InvalidSignature):
                webserver.validation.check_signature(**data)


class TestCheckAndFix(unittest.TestCase):
    """Tests for check_and_fix_values function"""

    def test_check_and_fix(self):
        """Test checking and fixing of kwargs."""
        normal_kwargs = {
            'balance_nat': 0,
            'deadline_nat': 1524386378,
            'some_nat': 144,
            'user_pubkey': 'GBDLXCJI2ZHCSQGSWWGUSTIBLPDCXWZWNR4KCDJFUBO2SRCHU6Q3NMQJ'

        }
        kwargs_set = [
            {
                'balance_nat': 0,
                'deadline_nat': 1524386378,
                'some_nat': 144,
                'user_pubkey': 'GBDLXCJI2ZHCSQGSWWGUSTIBLPDCXWZWNR4KCDJFUBO2SRCHU6Q3NMQJ'
            },
            {
                'balance_nat': '0',
                'deadline_nat': '1524386378',
                'some_nat': '144',
                'user_pubkey': 'GBDLXCJI2ZHCSQGSWWGUSTIBLPDCXWZWNR4KCDJFUBO2SRCHU6Q3NMQJ'
            }
        ]
        for kwargs in kwargs_set:
            with self.subTest(**kwargs):
                checked_and_fixed = webserver.validation.check_and_fix_values(kwargs)
                self.assertEqual(checked_and_fixed, normal_kwargs)

    def test_invalid_integer(self):
        """Test checking invalid integer"""
        kwargs_set = [
            {
                'balance_nat': 100000.0,
                'deadline_nat': 1524386378,
                'some_num': 144,
                'user_pubkey': 'GBDLXCJI2ZHCSQGSWWGUSTIBLPDCXWZWNR4KCDJFUBO2SRCHU6Q3NMQJ'
            },
            {
                'deadline_nat': '152438I378',
                'some_num': '144',
                'user_pubkey': 'GBDLXCJI2ZHCSQGSWWGUSTIBLPDCXWZWNR4KCDJFUBO2SRCHU6Q3NMQJ'
            },
            {
                'balance_nat': -25,
                'some_num': '144',
                'user_pubkey': 'GBDLXCJI2ZHCSQGSWWGUSTIBLPDCXWZWNR4KCDJFUBO2SRCHU6Q3NMQJ'
            }
        ]
        for kwargs in kwargs_set:
            with self.subTest(**kwargs), self.assertRaises(webserver.validation.InvalidField):
                webserver.validation.check_and_fix_values(kwargs)

    def test_invalid_pubkey(self):
        """Test checking invalid pubkey"""
        kwargs = {
            'balance_nat': 100000,
            'user_pubkey': 'GBDLcCJI2ZHC4SQGSWWGUSTIBPDCXWZWNR4KCDJFUBO2SRCHnQ3NMQJ'
        }
        with self.assertRaises(webserver.validation.InvalidField):
            webserver.validation.check_and_fix_values(kwargs)
