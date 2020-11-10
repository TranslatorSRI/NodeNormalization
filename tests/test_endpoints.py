"""Test node_normalizer server.py"""
import json
from node_normalizer.server import app
from starlette.testclient import TestClient
from pathlib import Path


class TestServer():

    @classmethod
    def setup_class(self):
        app.testing = True
        self.test_client = TestClient(app)

    @classmethod
    def teardown_class(self):
        self.test_client = None
