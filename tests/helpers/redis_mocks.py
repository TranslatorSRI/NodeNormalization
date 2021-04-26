"""
Functions that mock the redis response functions in normalizer.py
"""
import json
from pathlib import Path


async def mock_get_equivalent_curies(app, curie):
    """
    Mock the data returned by redis
    """
    if isinstance(curie, str):
        curie = curie.replace(':', '_')
    else:
        curie = curie.__root__.replace(':', '_')
    mock_redis = Path(__file__).parent.parent / 'resources' / 'mock-redis' / f'{curie}.json'
    if mock_redis.exists():
        with open(mock_redis, 'r') as json_data:
            equivalent_curies = json.load(json_data)
    else:
        equivalent_curies = {
            f"{curie}": None
        }
    return equivalent_curies
