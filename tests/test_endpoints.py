"""Test node_normalizer server.py"""
import json
from node_normalizer.server import app
from starlette.testclient import TestClient
from pathlib import Path
from unittest.mock import Mock, patch
from test_normalizer import find_diffs

# Need to add to sources root to avoid linter warnings
from helpers.redis_mocks import mock_get_equivalent_curies


premerged_response = Path(__file__).parent / 'resources' / 'premerged_response.json'
postmerged_response = Path(__file__).parent / 'resources' / 'postmerged_response.json'


premerged_dupe_edge = Path(__file__).parent / 'resources' / 'premerged_dupe_edge.json'
postmerged_dupe_edge = Path(__file__).parent / 'resources' / 'postmerged_dupe_edge.json'


input_set = Path(__file__).parent / 'resources' / 'input_set.json'

class TestServer:

    @classmethod
    def setup_class(self):
        app.testing = True
        self.test_client = TestClient(app)

    @classmethod
    def teardown_class(self):
        self.test_client = None

    @patch('node_normalizer.normalizer.get_equivalent_curies', Mock(side_effect=mock_get_equivalent_curies))
    def test_message_normalize_endpoint(self):
        """
        TODO turn this into a parametrized test for various cases
        """
        with open(premerged_response, 'r') as pre:
            premerged_data = json.load(pre)

        with open(postmerged_response, 'r') as post:
            postmerged_from_file = json.load(post)

        response = self.test_client.post('/response', json=premerged_data)
        postmerged_from_api = json.loads(response.text)
        
        # get the difference
        diffs = find_diffs(postmerged_from_api, postmerged_from_file)

        # no diffs, no problem
        assert diffs is None

    def test_real_result(self):
        with open('resources/ac_out_attributes.json', 'r') as pre:
            premerged_data = json.load(pre)

        response = self.test_client.post('/response', json=premerged_data)
        postmerged_from_api = json.loads(response.text)

        assert len(postmerged_from_api['message']['results']) == len(premerged_data['message']['results'])

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

        # get the difference
        diffs = find_diffs(postmerged_from_api, postmerged_from_file)

        # no diffs, no problem
        assert diffs is None

    @patch('node_normalizer.normalizer.get_equivalent_curies', Mock(side_effect=mock_get_equivalent_curies))
    def test_input_has_set(self):
        """
        Node normalizer is doing something bad with nodes when there are more than one knodes bound to a single qnode
        """
        with open(input_set, 'r') as pre:
            premerged_data = json.load(pre)

        response = self.test_client.post('/response', json=premerged_data)
        postmerged_from_api = json.loads(response.text)

        result = postmerged_from_api['message']['results'][0]
        #There are 2 coming in and no merging, so should be 2 going out
        assert len(result['edge_bindings']['treats']) == 2
        assert len(result['node_bindings']['drug']) == 2
