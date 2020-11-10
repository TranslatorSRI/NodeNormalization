import json
from typing import List, Dict, Optional, Any
from aioredis import Redis

from fastapi import FastAPI


def simple_normalize():
    """
    The simple normalizer takes a knowledge graph as input,
    and for each node converts the ID to the hash of the
    equivalent list, and merges identical nodes and their
    edges
    """


def priority_normalize():
    """
    The priority normalizer takes a knowledge graph as input
    and a namespace-semantic type priority map
    and for each node picks a clique leader based on it's
    namespace

    TO DO - handle cases where >1 nodes have the same ns

    alternatively this could come from kgx - see
    https://github.com/biolink/kgx/issues/224
    """



async def get_equivalent_curies(
        redis_connection0: Redis,
        redis_connection1: Redis,
        curie: List[str]
) -> List[str]:
    """
    Get equivalent curies using redis GET
    """
    # Get the equivalent list primary key identifier
    reference = await redis_connection0.get(curie, encoding='utf-8')
    if reference is None:
        return []
    value = await redis_connection1.get(reference, encoding='utf-8')
    return json.loads(value) if value is not None else []


async def get_normalized_nodes(app: FastAPI, curies: List[str]) -> Dict[str, Optional[str]]:
    """
    Get value(s) for key(s) using redis MGET
    """
    normal_nodes = {}
    references = await app.state.redis_connection0.mget(*curies, encoding='utf-8')
    references_nonan = [reference for reference in references if reference is not None]
    if references_nonan:
        values = await app.state.redis_connection1.mget(*references_nonan, encoding='utf-8')
        values = [json.loads(value) if value is not None else None for value in values]
        dereference = dict(zip(references_nonan, values))
        normal_nodes = {
            key: dereference[reference] if reference is not None else None
            for key, reference in zip(curies, references)
        }

    return normal_nodes


async def get_curie_prefixes(
        app: FastAPI,
        semantic_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get pivot table of semantic type x curie prefix
    """
    ret_val: dict = {}  # storage for the returned data

    # was an arg passed in
    if semantic_types:
        for item in semantic_types:
            # get the curies for this type
            curies = await app.state.redis_connection2.get(item, encoding='utf-8')

            # did we get any data
            if not curies:
                curies = '{' + f'"{item}"' + ': "Not found"}'

            curies = json.loads(curies)

            # set the return data
            ret_val[item] = {'curie_prefix': curies}
    else:
        types = await app.state.redis_connection2.lrange('semantic_types', 0, -1, encoding='utf-8')

        for item in types:
            # get the curies for this type
            curies = await app.state.redis_connection2.get(item, encoding='utf-8')

            # did we get any data
            if not curies:
                curies = '{' + f'"{item}"' + ': "Not found"}'

            curies = json.loads(curies)

            # set the return data
            ret_val[item] = {'curie_prefix': curies}

    return ret_val
