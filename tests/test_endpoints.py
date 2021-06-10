"""Test node_normalizer server.py"""
import json
from node_normalizer.server import app
from starlette.testclient import TestClient
from pathlib import Path
from unittest.mock import Mock, patch

# Need to add to sources root to avoid linter warnings
from helpers.redis_mocks import mock_get_equivalent_curies


premerged_response = Path(__file__).parent / 'resources' / 'premerged_response.json'
postmerged_response = Path(__file__).parent / 'resources' / 'postmerged_response.json'

premerged_dupe_edge = Path(__file__).parent / 'resources' / 'premerged_dupe_edge.json'
postmerged_dupe_edge = Path(__file__).parent / 'resources' / 'postmerged_dupe_edge.json'

from copy import deepcopy


def find_diffs(x, y, parent_key=None, exclude_keys=[], epsilon_keys=[]):
    """
    Take the diff of JSON-like dictionaries
    """
    EPSILON = 0.5
    rho = 1 - EPSILON

    if x == y:
        return None

    if parent_key in epsilon_keys:
        xfl, yfl = float_or_None(x), float_or_None(y)
        if xfl and yfl and xfl * yfl >= 0 and rho * xfl <= yfl and rho * yfl <= xfl:
            return None

    if type(x) != type(y) or type(x) not in [list, dict]:
        return x, y

    if type(x) == dict:
        d = {}
        for k in x.keys() ^ y.keys():
            if k in exclude_keys:
                continue
            if k in x:
                d[k] = (deepcopy(x[k]), None)
            else:
                d[k] = (None, deepcopy(y[k]))

        for k in x.keys() & y.keys():
            if k in exclude_keys:
                continue

            next_d = find_diffs(x[k], y[k], parent_key=k, exclude_keys=exclude_keys, epsilon_keys=epsilon_keys)
            if next_d is None:
                continue

            d[k] = next_d

        return d if d else None

    # assume a list:
    d = [None] * max(len(x), len(y))
    flipped = False
    if len(x) > len(y):
        flipped = True
        x, y = y, x

    for i, x_val in enumerate(x):
        d[i] = find_diffs(y[i], x_val, parent_key=i, exclude_keys=exclude_keys, epsilon_keys=epsilon_keys) if flipped else find_diffs(x_val, y[i], parent_key=i, exclude_keys=exclude_keys, epsilon_keys=epsilon_keys)

    for i in range(len(x), len(y)):
        d[i] = (y[i], None) if flipped else (None, y[i])

    return None if all(map(lambda x: x is None, d)) else d

# We need this helper function as well:
def float_or_None(x):
    try:
        return float(x)
    except ValueError:
        return None

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
        
        # get the difference
        difs = find_diffs(postmerged_from_api, postmerged_from_file)

        assert difs is None

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
        difs = find_diffs(postmerged_from_api, postmerged_from_file)

        # dictionary equality might be brittle
        assert difs is None
