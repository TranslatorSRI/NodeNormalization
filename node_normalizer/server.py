"""FastAPI server."""
import os
from typing import List, Optional, Dict

import aioredis
from fastapi import FastAPI, HTTPException, Query
from reasoner_pydantic import KnowledgeGraph

from .loader import NodeLoader
from .apidocs import get_app_info
from .model import SemanticTypes, CuriePivot, CurieList, SemanticTypesInput
from .normalizer import get_normalized_nodes, get_curie_prefixes, normalize_kg

# Some metadata not implemented see
# https://github.com/tiangolo/fastapi/pull/1812
app = FastAPI(**get_app_info())

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
    await app.state.redis_connection0.wait_closed()
    app.state.redis_connection1.close()
    await app.state.redis_connection1.wait_closed()
    app.state.redis_connection2.close()
    await app.state.redis_connection2.wait_closed()


@app.post(
    '/knowledge_graph',
    summary='Normalizes a TRAPI compliant knowledge graph',
    description='Returns the knowledge graph with merged nodes and edges'
)
async def normalize_kgraph(kgraph: KnowledgeGraph) -> KnowledgeGraph:
    """
    Normalizes a TRAPI compliant knowledge graph
    """
    return KnowledgeGraph.parse_obj(await normalize_kg(app, kgraph))


@app.get(
    '/get_normalized_nodes',
    summary='Get the equivalent identifiers and semantic types for the curie(s) entered.',
    description='Returns the equivalent identifiers and semantic types for the curie(s)'
)
async def get_normalized_node_handler(curie: List[str] = Query(['MESH:D014867', 'NCIT:C34373'])):
    """
    Get value(s) for key(s) using redis MGET
    """
    normalized_nodes = await get_normalized_nodes(app, curie)

    if not normalized_nodes:
        raise HTTPException(detail='No matches found for the specified curie(s).', status_code=404)

    return normalized_nodes


@app.post(
    '/get_normalized_nodes',
    summary='Get the equivalent identifiers and semantic types for the curie(s) entered.',
    description='Returns the equivalent identifiers and semantic types for the curie(s)'
)
async def get_normalized_node_handler(curies: CurieList):
    """
    Get value(s) for key(s) using redis MGET
    """
    normalized_nodes = await get_normalized_nodes(app, curies.curies)

    if not normalized_nodes:
        raise HTTPException(detail='No matches found for the specified curie(s).', status_code=404)

    return normalized_nodes


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
            [],
            description="e.g. chemical_substance, anatomical_entity"
        )
) -> Dict[str, CuriePivot]:

    return await get_curie_prefixes(app, semantic_type)


@app.post(
    '/get_curie_prefixes',
    response_model=Dict[str, CuriePivot],
    summary='Return the number of times each CURIE prefix appears in an equivalent identifier for a semantic type',
    description='Returns the curies and their hit count for a semantic type(s).'
)
async def get_curie_prefixes_handler(semantic_types: SemanticTypesInput) -> Dict[str, CuriePivot]:

    return await get_curie_prefixes(app, semantic_types.semantic_types)
