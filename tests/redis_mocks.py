"""
Functions that mock the redis response functions in normalizer.py

TODO figure out better way to get this imported see
https://stackoverflow.com/a/33515264
https://stackoverflow.com/q/50796370

"""
import json
from pathlib import Path


async def mock_get_equivalent_curies(app, curie):
    """
    Mock the data returned by redis
    """
    curie = curie.replace(':', '_')
    mock_redis = Path(__file__).parent / 'resources' / 'mock-redis' / f'{curie}.json'
    with open(mock_redis, 'r') as json_data:
        equivalent_curies = json.load(json_data)
    return equivalent_curies
