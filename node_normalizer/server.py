"""FastAPI server."""
import asyncio
import os
import traceback

from pathlib import Path
from typing import List, Optional, Dict
from fastapi.middleware.cors import CORSMiddleware
import requests
from requests.adapters import HTTPAdapter, Retry
import fastapi
from fastapi import FastAPI, HTTPException
import reasoner_pydantic
from bmt import Toolkit
from starlette.responses import JSONResponse

from .loader import NodeLoader
from .apidocs import get_app_info, construct_open_api_schema
from .model import (
    SemanticTypes,
    CuriePivot,
    CurieList,
    SemanticTypesInput,
    ConflationList,
)
from .normalizer import get_normalized_nodes, get_curie_prefixes, normalize_message
from .redis_adapter import RedisConnectionFactory
from .util import LoggingUtil

logger = LoggingUtil.init_logging()

# Some metadata not implemented see
# https://github.com/tiangolo/fastapi/pull/1812
app = FastAPI(**get_app_info())

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

loader = NodeLoader()

redis_host = os.environ.get("REDIS_HOST", loader.get_config()["redis_host"])
redis_port = os.environ.get("REDIS_PORT", loader.get_config()["redis_port"])
TRAPI_VERSION = os.environ.get("TRAPI_VERSION", "1.4")

async_query_tasks = set()


@app.on_event("startup")
async def startup_event():
    """
    Start up Redis connection
    """
    redis_config_file = Path(__file__).parent.parent / "redis_config.yaml"
    connection_factory = await RedisConnectionFactory.create_connection_pool(redis_config_file)
    app.state.redis_connection0 = connection_factory.get_connection(connection_id="eq_id_to_id_db")
    app.state.redis_connection1 = connection_factory.get_connection(connection_id="id_to_eqids_db")
    app.state.redis_connection2 = connection_factory.get_connection(connection_id="id_to_type_db")
    app.state.redis_connection3 = connection_factory.get_connection(connection_id="curie_to_bl_type_db")
    app.state.redis_connection4 = connection_factory.get_connection(connection_id="info_content_db")
    app.state.redis_connection5 = connection_factory.get_connection(connection_id="gene_protein_db")
    app.state.redis_connection6 = connection_factory.get_connection(connection_id="chemical_drug_db")
    app.state.toolkit = Toolkit()
    app.state.ancestor_map = {}


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
    app.state.redis_connection3.close()
    await app.state.redis_connection3.wait_closed()
    app.state.redis_connection4.close()
    await app.state.redis_connection4.wait_closed()
    app.state.redis_connection5.close()
    await app.state.redis_connection5.wait_closed()
    app.state.redis_connection6.close()
    await app.state.redis_connection6.wait_closed()


@app.post(
    "/query",
    summary="Normalizes a TRAPI response object",
    description="Returns the response object with a merged knowledge graph and query graph bindings",
    response_model=reasoner_pydantic.Query,
    response_model_exclude_none=True,
    response_model_exclude_unset=True
)
async def query(query: reasoner_pydantic.Query) -> reasoner_pydantic.Query:
    """
    Normalizes a TRAPI compliant knowledge graph
    """
    query.message = await normalize_message(app, query.message)
    return query


@app.post(
    "/asyncquery",
    summary="Normalizes a TRAPI response object",
    description="Returns the response object with a merged knowledge graph and query graph bindings",
)
async def async_query(async_query: reasoner_pydantic.AsyncQuery):
    """
    Normalizes a TRAPI compliant knowledge graph
    """
    # need a strong reference to task such that GC doesn't remove it mid execution...https://docs.python.org/3/library/asyncio-task.html#creating-tasks
    task = asyncio.create_task(async_query_task(async_query))
    async_query_tasks.add(task)
    task.add_done_callback(async_query_tasks.discard)

    return JSONResponse(content={"description": f"Query commenced. Will send result to {async_query.callback}"}, status_code=200)


async def async_query_task(async_query: reasoner_pydantic.AsyncQuery):
    try:
        async_query.message = await normalize_message(app, async_query.message)
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=[
                "HEAD",
                "GET",
                "PUT",
                "DELETE",
                "OPTIONS",
                "TRACE",
                "POST",
            ],
        )
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        logger.info(f"sending callback to: {async_query.callback}")

        post_response = session.post(
            url=async_query.callback,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            data=async_query.json(),
        )
        logger.info(f"async_query post status code: {post_response.status_code}")
    except BaseException as e:
        logger.exception(e)


@app.get(
    "/get_allowed_conflations",
    summary="Get the available conflations",
    description="The returned strings can be included in an option to /get_normalized_nodes",
)
async def get_conflations() -> ConflationList:
    """
    Get implemented conflations
    """
    # TODO: build from config instead of hard-coding.
    conflations = ConflationList(conflations=["GeneProtein"])

    return conflations


@app.get(
    "/get_normalized_nodes",
    summary="Get the equivalent identifiers and semantic types for the curie(s) entered.",
    description="Returns the equivalent identifiers and semantic types for the curie(s)",
)
async def get_normalized_node_handler(
    curie: List[str] = fastapi.Query(
        [],
        description="List of curies to normalize",
        example=["MESH:D014867", "NCIT:C34373"],
        min_items=1,
    ),
    conflate: bool = fastapi.Query(True, description="Whether to apply gene/protein conflation"),
    drug_chemical_conflate: bool = fastapi.Query(False, description="Whether to apply drug/chemical conflation"),
    description: bool = fastapi.Query(False, description="Whether to return curie descriptions when possible")
):
    """
    Get value(s) for key(s) using redis MGET
    """
    # no_conflate = request.args.get('dontconflate',['GeneProtein'])
    normalized_nodes = await get_normalized_nodes(app, curie, conflate, drug_chemical_conflate, include_descriptions=description)

    # If curie contains at least one entry, then the only way normalized_nodes could be blank
    # would be if an error occurred during processing.
    if not normalized_nodes:
        raise HTTPException(detail="Error occurred during processing.", status_code=500)

    return normalized_nodes


@app.post(
    "/get_normalized_nodes",
    summary="Get the equivalent identifiers and semantic types for the curie(s) entered.",
    description="Returns the equivalent identifiers and semantic types for the curie(s). Use the `conflate` flag to choose whether to apply conflation.",
)
async def get_normalized_node_handler(curies: CurieList):
    """
    Get value(s) for key(s) using redis MGET
    """
    normalized_nodes = await get_normalized_nodes(app, curies.curies, curies.conflate, curies.drug_chemical_conflate, curies.description)

    # If curies.curies contains at least one entry, then the only way normalized_nodes could be blank
    # would be if an error occurred during processing.
    if not normalized_nodes:
        raise HTTPException(detail="Error occurred during processing.", status_code=500)

    return normalized_nodes


@app.get(
    "/get_semantic_types",
    response_model=SemanticTypes,
    summary="Return a list of BioLink semantic types for which normalization has been attempted.",
    description="Returns a distinct set of the semantic types discovered in the compendium data.",
)
async def get_semantic_types_handler() -> SemanticTypes:
    # look for all biolink semantic types
    types = await app.state.redis_connection3.lrange("semantic_types", 0, -1, encoding="utf-8")

    # did we get any data
    if not types:
        raise HTTPException(detail="No semantic types discovered.", status_code=404)

    # get the distinct list of Biolink model types in the correct format
    # https://github.com/TranslatorSRI/NodeNormalization/issues/29
    ret_val = SemanticTypes(semantic_types={"types": types})

    # return the data to the caller
    return ret_val


@app.get(
    "/get_curie_prefixes",
    response_model=Dict[str, CuriePivot],
    summary="Return the number of times each CURIE prefix appears in an equivalent identifier for a semantic type",
    description="Returns the curies and their hit count for a semantic type(s).",
)
async def get_curie_prefixes_handler(
    semantic_type: Optional[List[str]] = fastapi.Query([], description="e.g. chemical_substance, anatomical_entity")
) -> Dict[str, CuriePivot]:
    return await get_curie_prefixes(app, semantic_type)


@app.post(
    "/get_curie_prefixes",
    response_model=Dict[str, CuriePivot],
    summary="Return the number of times each CURIE prefix appears in an equivalent identifier for a semantic type",
    description="Returns the curies and their hit count for a semantic type(s).",
)
async def get_curie_prefixes_handler(
    semantic_types: SemanticTypesInput,
) -> Dict[str, CuriePivot]:
    return await get_curie_prefixes(app, semantic_types.semantic_types)


# Override open api schema with custom schema
app.openapi_schema = construct_open_api_schema(app)
