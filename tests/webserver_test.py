"""Tests for webserver package."""
from unittest import TestCase
from multiprocessing import Process
from time import sleep

from requests import Session, RequestException
import flask

import webserver
import webserver.validation

HOST = '127.0.0.1'
PORT = 5000


class TestLogger(TestCase):
    """Testing webserver."""

    @classmethod
    def setUpClass(cls):
        """Register blueprint with single endpoint and runs web server in separate process"""
        blueprint = flask.Blueprint('test', __name__)

        @blueprint.route('/ping', methods=['GET'])
        # pylint: disable=unused-variable
        def ping():
            """Returns `pong` as answer to request"""
            return 'pong'

        webserver.APP.register_blueprint(blueprint)

        cls._webserver_process = Process(target=lambda: webserver.APP.run(host=HOST, port=PORT, debug=True))
        cls._webserver_process.start()

        cls._session = Session()
        # It is necessary in case when the test is run before the web server finishes its launch
        sleep(7)

    def test_server_accessibility(self):
        """Tests server accessibility"""
        response = self._session.get(url='http://{host}:{port}/ping'.format(host=HOST, port=PORT))
        self.assertEqual(response.text, 'pong')

    @classmethod
    def tearDownClass(cls):
        """Terminates web server process"""
        cls._webserver_process.terminate()
        cls._webserver_process.join()
        del cls._webserver_process
        del cls._session
