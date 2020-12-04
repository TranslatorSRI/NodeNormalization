"""Test node_normalizer server.py"""
import json
from node_normalizer.server import app
from starlette.testclient import TestClient
from pathlib import Path
from unittest.mock import Mock, patch
from tests.redis_mocks import mock_get_equivalent_curies


premerged_graph = Path(__file__).parent / 'resources' / 'premerged_kgraph.json'
postmerged_graph = Path(__file__).parent / 'resources' / 'postmerged_kgraph.json'


class TestServer:

    @classmethod
    def setup_class(self):
        app.testing = True
        self.test_client = TestClient(app)

    @classmethod
    def teardown_class(self):
        self.test_client = None

    @patch('node_normalizer.normalizer.get_equivalent_curies', Mock(side_effect=mock_get_equivalent_curies))
    def test_kg_normalize(self):
        with open(premerged_graph, 'r') as pre:
            premerged_data = json.load(pre)

        with open(postmerged_graph, 'r') as post:
            postmerged_from_file = json.load(post)

        response = self.test_client.post('/message', json=premerged_data)
        postmerged_from_api = json.loads(response.text)
        
        # dictionary equality might be brittle
        assert postmerged_from_api == postmerged_from_file
