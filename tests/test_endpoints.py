import pytest
from src.server import app

def test_semantic_type_endpoint():
    # make a good request
    request, response = app.test_client.post('/get_semantic_types')

    # was the request successful
    assert(response.status == 200)


def test_cureie_prefixes_endpoint():
    pass

def test_normalized_nodes_endpoint():
    pass
