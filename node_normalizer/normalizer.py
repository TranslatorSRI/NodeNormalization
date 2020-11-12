import json
from typing import List, Dict, Optional, Any, Union, Set, Tuple

from fastapi import FastAPI
from reasoner_pydantic import KnowledgeGraph


async def normalize_kg(app: FastAPI, kgraph: KnowledgeGraph) -> Dict:
    """
    Given a TRAPI knowledge graph creates a merged graph
    by iterating over each node, getting the primary id,
    and merging nodes and edges (as needed)
    """
    # cache for primary node ids
    primary_nodes_seen = set()

    # cache for nodes
    nodes_seen = set()

    # cache for source,relation,target tuples
    edges_seen: Set[Tuple[str, str, str]] = set()

    # Map for each id and its primary id
    id_primary_id: Dict[str, str] = {}

    merged_kgraph: Dict = {
        'nodes': [],
        'edges': []
    }

    for node in kgraph.nodes:
        if node.id in nodes_seen:
            continue

        nodes_seen.add(node.id)
        id_primary_id[node.id] = node.id  # expected to overridden by primary id

        merged_node = node.dict()

        equivalent_curies = await get_equivalent_curies(app, node.id)

        if node.id in equivalent_curies:
            primary_id = equivalent_curies[node.id]['id']['identifier']
            id_primary_id[node.id] = primary_id

            if primary_id in primary_nodes_seen:
                continue

            primary_nodes_seen.add(primary_id)

            if 'label' in equivalent_curies[node.id]['id']:
                primary_label = equivalent_curies[node.id]['id']['label']
            elif 'name' in merged_node:
                primary_label = merged_node['name']
            else:
                primary_label = ''

            merged_node['id'] = primary_id
            merged_node['name'] = primary_label

            if 'equivalent_identifiers' in equivalent_curies[node.id]:
                merged_node['same_as'] = [
                    node['identifier']
                    for node in equivalent_curies[node.id]['equivalent_identifiers']
                ]
            if 'type' in equivalent_curies[node.id]:
                merged_node['category'] = [
                    'biolink:' + _to_upper_camel_case(category)
                    for category in equivalent_curies[node.id]['type']
                ]

        merged_kgraph['nodes'].append(merged_node)

    for edge in kgraph.edges:
        triple = (
            id_primary_id[edge.source_id],
            edge.type,
            id_primary_id[edge.target_id]
        )
        if triple in edges_seen:
            continue

        edges_seen.add(triple)
        merged_edge = edge.dict()
        merged_edge['source_id'] = id_primary_id[edge.source_id]
        merged_edge['target_id'] = id_primary_id[edge.target_id]

        merged_kgraph['edges'].append(merged_edge)

    return merged_kgraph


async def get_equivalent_curies(
        app: FastAPI,
        curie: str
) -> Dict:
    """
    Get primary id and equivalent curies using redis GET

    Returns either an empty list or a list containing two
    dicts with the format:
    {
      ${curie}: {'identifier': 'foo', 'label': bar},
      'equivalent_identifiers': [{'identifier': 'foo', 'label': bar}, ...]
    }
    """
    # Get the equivalent list primary key identifier
    reference = await app.state.redis_connection0.get(curie, encoding='utf-8')
    if reference is None:
        return {}
    value = await app.state.redis_connection1.get(reference, encoding='utf-8')
    return json.loads(value) if value is not None else {}


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


def _to_upper_camel_case(snake_str):
    """
    credit https://stackoverflow.com/a/19053800
    """
    return ''.join(x.title() for x in snake_str.split('_'))