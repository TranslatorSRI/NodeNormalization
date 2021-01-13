"""Test node_normalizer server.py"""
import json
from node_normalizer.server import app
from starlette.testclient import TestClient


class MockRedis():
    async def mget(self, *args, **kwargs):
        return [None for _ in args]


app.state.redis_connection0 = MockRedis()
app.state.redis_connection1 = MockRedis()


def test_not_found():
    client = TestClient(app)
    response = client.get('/get_normalized_nodes', params={"curie": ["UNKNOWN:000000"]})
    result = json.loads(response.text)
    assert result == {"UNKNOWN:000000": None}
    response = client.post('/get_normalized_nodes', json={"curies": ["UNKNOWN:000000"]})
    result = json.loads(response.text)
    assert result == {"UNKNOWN:000000": None}


def test_empty():
    client = TestClient(app)
    response = client.get('/get_normalized_nodes', params={"curie": []})
    result = json.loads(response.text)
    assert result == dict()
    response = client.post('/get_normalized_nodes', json={"curies": []})
    result = json.loads(response.text)
    assert result == dict()
