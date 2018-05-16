"""Tests for webserver package."""
import unittest
import flask
import webserver


class TestWebserver(unittest.TestCase):
    """Testing webserver."""

    @classmethod
    def setUpClass(cls):
        """Register blueprint with single endpoint and prepare test client"""
        blueprint = flask.Blueprint('test', __name__)

        @blueprint.route('/ping', methods=['GET'])
        # pylint: disable=unused-variable
        def ping():
            """Returns `pong` as answer to request"""
            return 'pong'

        webserver.APP.register_blueprint(blueprint)
        cls._client = webserver.APP.test_client()

    def test_server_accessibility(self):
        """Tests server accessibility"""
        response = self._client.get('/ping')
        self.assertEqual(response.data, b'pong')

    @classmethod
    def tearDownClass(cls):
        """Terminates web server process"""
        del cls._client
