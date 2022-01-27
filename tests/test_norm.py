"""Test node_normalizer server.py"""
import json
from node_normalizer.server import app
from starlette.testclient import TestClient


from unittest.mock import Mock, patch
from helpers.redis_mocks import mock_get_equivalent_curies, mock_get_ic

from pathlib import Path
import os

class MockRedis():
    def __init__(self, data):
        self.data = data
    async def mget(self, *args, **kwargs):
        return [self.data[x]  if x in self.data else None for x in args ]

import json
#Id -> Canonical
app.state.redis_connection0 = MockRedis({"DOID:3812":"MONDO:0005002", "MONDO:0005002":"MONDO:0005002"})
#Canonical->Equiv
app.state.redis_connection1 = MockRedis({"MONDO:0005002":json.dumps([{"i":"MONDO:0005002"},{"i":"DOID:3812"}])})
app.state.redis_connection2 = MockRedis({"MONDO:0005002":"biolink:Disease"})
app.state.redis_connection3 = MockRedis({})
app.state.redis_connection4 = MockRedis({})
app.state.redis_connection5 = MockRedis({})
app.state.ancestor_map={"biolink:Disease":["biolink:Disease","biolink:NamedThing"]}


def test_not_found():
    client = TestClient(app)
    response = client.get('/get_normalized_nodes', params={"curie": ["UNKNOWN:000000"]})
    result = json.loads(response.text)
    assert result == {"UNKNOWN:000000": None}
    response = client.post('/get_normalized_nodes', json={"curies": ["UNKNOWN:000000"]})
    result = json.loads(response.text)
    assert result == {"UNKNOWN:000000": None}

def test_one_missing():
    client = TestClient(app)
    response = client.get('/get_normalized_nodes', params={"curie": ["UNKNOWN:000000", "DOID:3812"]})
    result = json.loads(response.text)
    assert len(result) == 2
    assert result['UNKNOWN:000000'] == None
    assert result['DOID:3812']['id']['identifier'] == 'MONDO:0005002'

def test_merge():
    client = TestClient(app)
    response = client.get('/get_normalized_nodes', params={"curie": ["MONDO:0005002", "DOID:3812"]})
    result = json.loads(response.text)
    assert len(result) == 2
    assert 'MONDO:0005002' in result
    assert 'DOID:3812' in result


def test_empty():
    client = TestClient(app)
    response = client.get('/get_normalized_nodes', params={"curie": []})
    result = json.loads(response.text)
    assert result == dict()
    response = client.post('/get_normalized_nodes', json={"curies": []})
    result = json.loads(response.text)
    assert result == dict()


def test_without_resolvable_curies():
    """
    /get_normalized_nodes previously returned {} if none of the provided CURIEs are resolvable.
    This test ensures that that bug has been fixed.

    Reported in https://github.com/TranslatorSRI/NodeNormalization/issues/113
    """
    client = TestClient(app)
    response = client.get('/get_normalized_nodes', params={"curies": ["NCBIGene:ABCD", "NCBIGene:GENE:1017"]})
    result = json.loads(response.text)
    assert result == {
        'NCBIGene:ABCD': None,
        'NCBIGene:GENE:1017': None
    }
