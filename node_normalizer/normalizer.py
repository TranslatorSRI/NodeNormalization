import json
from typing import List, Dict, Optional, Any, Union, Set, Tuple

from fastapi import FastAPI
from reasoner_pydantic import KnowledgeGraph


async def normalize_kgraph(app: FastAPI, kgraph: KnowledgeGraph) -> KnowledgeGraph:
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
        'nodes': {},
        'edges': {}
    }

    for node_id, node in kgraph.nodes.items():
        if node_id in nodes_seen:
            continue

        nodes_seen.add(node_id)
        id_primary_id[node_id] = node_id  # expected to overridden by primary id

        merged_node = node.dict()

        equivalent_curies = await get_equivalent_curies(app, node_id)

        if node_id in equivalent_curies:
            primary_id = equivalent_curies[node_id]['id']['identifier']
            id_primary_id[node_id] = primary_id

            if primary_id in primary_nodes_seen:
                continue

            primary_nodes_seen.add(primary_id)

            if 'label' in equivalent_curies[node_id]['id']:
                primary_label = equivalent_curies[node_id]['id']['label']
            elif 'name' in merged_node:
                primary_label = merged_node['name']
            else:
                primary_label = ''

            merged_node['name'] = primary_label

            # TODO define behavior if there is already a same_as attribute
            if 'equivalent_identifiers' in equivalent_curies[node_id]:
                merged_node['attributes'] = [
                    {
                        'type': 'biolink:same_as',
                        'value': [
                            node['identifier']
                            for node in equivalent_curies[node_id]['equivalent_identifiers']
                        ],
                        'name': 'same_as',

                        # TODO, should we add the app version as the source
                        # or perhaps the babel/redis cache version
                        # This will make unit testing a little more tricky
                        # see https://stackoverflow.com/q/57624731

                        # 'source': f'{app.title} {app.version}',
                    }
                ]

            if 'type' in equivalent_curies[node_id]:
                merged_node['category'] = equivalent_curies[node_id]['type']

            merged_kgraph['nodes'][primary_id] = merged_node
        else:
            merged_kgraph['nodes'][node_id] = merged_node

    for edge_id, edge in kgraph.edges.items():
        # Accessing __root__ directly seems wrong,
        # https://github.com/samuelcolvin/pydantic/issues/730
        # could also do str(edge.subject)
        if edge.subject.__root__ in id_primary_id:
            primary_subject = id_primary_id[edge.subject.__root__]
        else:
            # should we throw a validation error here?
            primary_subject = edge.subject

        if edge.object.__root__ in id_primary_id:
            primary_object = id_primary_id[edge.object.__root__]
        else:
            primary_object = edge.object

        triple = (
            primary_subject,
            edge.predicate.__root__,
            primary_object
        )
        if triple in edges_seen:
            continue

        edges_seen.add(triple)
        merged_edge = edge.dict()

        merged_edge['subject'] = primary_subject
        merged_edge['object'] = primary_object
        merged_kgraph['edges'][edge_id] = merged_edge

    return KnowledgeGraph.parse_obj(merged_kgraph)


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
      'type': ['named_thing']
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
