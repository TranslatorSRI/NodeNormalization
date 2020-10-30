import json
from typing import List, Dict, Optional, Any

from fastapi import FastAPI


async def get_normalized_nodes(app: FastAPI, curies: List[str]) -> Dict[str, Optional[str]]:
    """
    Get value(s) for key(s) using redis MGET
    """
    normal_nodes = {}
    references = await app.state.redis_connection0.mget(*curies, encoding='utf-8')
    references_nonnan = [reference for reference in references if reference is not None]
    if references_nonnan:
        values = await app.state.redis_connection1.mget(*references_nonnan, encoding='utf-8')
        values = [json.loads(value) if value is not None else None for value in values]
        dereference = dict(zip(references_nonnan, values))
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

    print(semantic_types)

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