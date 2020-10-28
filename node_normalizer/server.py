"""FastAPI server."""
import json
import os
from typing import List, Optional, Dict

import aioredis
from fastapi import FastAPI, HTTPException, Query

from .loader import NodeLoader
from .apidocs import app_info
from .model.response import SemanticTypes, CuriePivot

# Some metadata not implemented see
# https://github.com/tiangolo/fastapi/pull/1812
app = FastAPI(**app_info)

loader = NodeLoader()

redis_host = os.environ.get('REDIS_HOST', loader.get_config()['redis_host'])
redis_port = os.environ.get('REDIS_PORT', loader.get_config()['redis_port'])


@app.on_event('startup')
async def startup_event():
    """
    Start up Redis connection
    """
    app.state.redis_connection0 = await aioredis.create_redis_pool(
        f'redis://{redis_host}:{redis_port}', db=0)
    app.state.redis_connection1 = await aioredis.create_redis_pool(
        f'redis://{redis_host}:{redis_port}', db=1)
    app.state.redis_connection2 = await aioredis.create_redis_pool(
        f'redis://{redis_host}:{redis_port}', db=2)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Shut down Redis connection
    """
    app.state.redis_connection0.close()
    await app.redis_connection0.wait_closed()
    app.state.redis_connection1.close()
    await app.redis_connection2.wait_closed()
    app.state.redis_connection2.close()
    await app.redis_connection2.wait_closed()


@app.get(
    '/get_normalized_nodes',
    summary='Get the equivalent identifiers and semantic types for the curie(s) entered.',
    description='Returns the equivalent identifiers and semantic types for the curie(s)'
)
async def get_normalized_node_handler(curie: List[str] = Query(['MESH:D014867', 'NCIT:C34373'])):
    """
    Get value(s) for key(s) using redis MGET
    """
    references = await app.state.redis_connection0.mget(*curie, encoding='utf-8')
    references_nonnan = [reference for reference in references if reference is not None]
    if not references_nonnan:
        raise HTTPException(detail='No matches found for the specified curie(s).', status_code=404)
    values = await app.state.redis_connection1.mget(*references_nonnan, encoding='utf-8')
    values = [json.loads(value) if value is not None else None for value in values]
    dereference = dict(zip(references_nonnan, values))

    return {
        key: dereference[reference] if reference is not None else None
        for key, reference in zip(curie, references)
    }


@app.get(
    '/get_semantic_types',
    response_model=SemanticTypes,
    summary='Return a list of BioLink semantic types for which normalization has been attempted.',
    description='Returns a distinct set of the semantic types discovered in the compendium data.'
)
async def get_semantic_types_handler() -> SemanticTypes:
    # look for all biolink semantic types
    types = await app.state.redis_connection2.lrange('semantic_types', 0 ,-1, encoding='utf-8')

    # did we get any data
    if not types:
        raise HTTPException(detail='No semantic types discovered.', status_code=404)

    # get the distinct list of Biolink model types in the correct format
    ret_val = SemanticTypes(
        semantic_types= {'types': types}
    )

    # return the data to the caller
    return ret_val


@app.get(
    '/get_curie_prefixes',
    response_model=Dict[str, CuriePivot],
    summary='Return the number of times each CURIE prefix appears in an equivalent identifier for a semantic type',
    description='Returns the curies and their hit count for a semantic type(s).'
)
async def get_curie_prefixes_handler(
        semantic_type: Optional[List[str]] = Query(
            None,
            description="e.g. chemical_substance, anatomical_entity"
        )
) -> Dict[str, CuriePivot]:
    # storage for the returned data
    ret_val: dict = {}

    # was an arg passed in
    if semantic_type:
        for item in semantic_type:
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
