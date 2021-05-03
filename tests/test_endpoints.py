"""Test node_normalizer server.py"""
import json
from node_normalizer.server import app
from starlette.testclient import TestClient
from pathlib import Path
from unittest.mock import Mock, patch

# Need to add to sources root to avoid linter warnings
from redis_mocks import mock_get_equivalent_curies


premerged_response = Path(__file__).parent / 'resources' / 'premerged_response.json'
postmerged_response = Path(__file__).parent / 'resources' / 'postmerged_response.json'

premerged_dupe_edge = Path(__file__).parent / 'resources' / 'premerged_dupe_edge.json'
postmerged_dupe_edge = Path(__file__).parent / 'resources' / 'postmerged_dupe_edge.json'


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
        """
        TODO turn this into a parametrized test for various cases
        """
        with open(premerged_response, 'r') as pre:
            premerged_data = json.load(pre)

        with open(postmerged_response, 'r') as post:
            postmerged_from_file = json.load(post)

        response = self.test_client.post('/response', json=premerged_data)
        postmerged_from_api = json.loads(response.text)
        
        # dictionary equality might be brittle
        assert postmerged_from_api == postmerged_from_file

    @patch('node_normalizer.normalizer.get_equivalent_curies', Mock(side_effect=mock_get_equivalent_curies))
    def test_dupe_edge(self):
        """
        TODO turn this into a parametrized test for various cases
        """
        with open(premerged_dupe_edge, 'r') as pre:
            premerged_data = json.load(pre)

        with open(postmerged_dupe_edge, 'r') as post:
            postmerged_from_file = json.load(post)

        response = self.test_client.post('/response', json=premerged_data)
        postmerged_from_api = json.loads(response.text)

        # dictionary equality might be brittle
        assert postmerged_from_api == postmerged_from_file
