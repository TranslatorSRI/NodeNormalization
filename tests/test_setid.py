"""Test node_normalizer server.py"""
import json
from node_normalizer.server import app
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from .helpers.redis_mocks import mock_get_equivalent_curies, mock_get_ic
from pathlib import Path
import os
from bmt import Toolkit


class MockRedis:
    def __init__(self, data):
        self.data = data

    async def mget(self, *args, **kwargs):
        return [self.data[x] if x in self.data else None for x in args]


# Id -> Canonical
app.state.eq_id_to_id_db = MockRedis(
    {"DOID:3812": "MONDO:0005002", "MONDO:0005002": "MONDO:0005002"}
)
# Canonical->Equiv
app.state.id_to_eqids_db = MockRedis(
    {"MONDO:0005002": json.dumps([{"i": "MONDO:0005002"}, {"i": "DOID:3812"}])}
)
app.state.id_to_type_db = MockRedis({"MONDO:0005002": "biolink:Disease"})
app.state.curie_to_bl_type_db = MockRedis({})
app.state.info_content_db = MockRedis({})
app.state.toolkit = Toolkit()
app.state.ancestor_map = {}

# TODO: add test for conflations.

def test_setid_empty():
    """
    Make sure we get a sensible response if we call setid without any parameters.
    """
    client = TestClient(app)
    response = client.get("/get_setid")
    result = response.json()
    assert result == {
        "detail":
            [
                {
                    "loc": ["query", "curie"],
                    "msg": "ensure this value has at least 1 items",
                    "type": "value_error.list.min_items",
                    "ctx": { "limit_value": 1 }
                }
            ]
    }


def test_setid_basic():
    """
    Some basic tests to make sure normalization works as expected.
    """
    client = TestClient(app)

    expected_setid = [
        {
            'curie': ['DOID:3812', 'MONDO:0005002', 'MONDO:0005003', ''],
            'normalized_curies': ['MONDO:0005002', 'MONDO:0005003']
        }
    ]

    response = client.get("/get_setid", params={
        ''
    })
    result = response.json()