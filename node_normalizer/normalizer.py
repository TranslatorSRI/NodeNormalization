import json
from typing import List, Dict, Optional, Any, Set, Tuple, Union

from fastapi import FastAPI
from reasoner_pydantic import KnowledgeGraph, Message, QueryGraph, Result, CURIE


async def normalize_message(app: FastAPI, message: Message) -> Message:
    """
    Given a TRAPI message, updates the message to include a
    normalized qgraph, kgraph, and results
    """
    merged_qgraph = await normalize_qgraph(app, message.query_graph)
    merged_kgraph, node_id_map, edge_id_map = await normalize_kgraph(app, message.knowledge_graph)
    merged_results = await normalize_results(message.results, node_id_map, edge_id_map)

    return Message.parse_obj({
        'query_graph': merged_qgraph,
        'knowledge_graph': merged_kgraph,
        'results': merged_results
    })


async def normalize_results(
        results: List[Result],
        node_id_map: Dict[str, str],
        edge_id_map: Dict[str, str]
) -> List[Result]:
    """
    Given a TRAPI result creates a normalized result object
    """
    merged_results: List[Result] = []
    for result in results:
        merged_result = {
            'node_bindings': {},
            'edge_bindings': {}
        }
        for node_code, node_bindings in result.node_bindings.items():
            merged_node_bindings = []
            for n_bind in node_bindings:
                merged_binding = n_bind.dict()
                merged_binding['id'] = node_id_map[n_bind.id.__root__]
                merged_node_bindings.append(merged_binding)
            merged_result['node_bindings'][node_code] = merged_node_bindings

        for edge_code, edge_bindings in result.edge_bindings.items():
            merged_edge_bindings = []
            for e_bind in edge_bindings:
                merged_binding = e_bind.dict()
                merged_binding['id'] = edge_id_map[e_bind.id]
                merged_edge_bindings.append(merged_binding)
            merged_result['edge_bindings'][edge_code] = merged_edge_bindings

        merged_results.append(Result.parse_obj(merged_result))

    return merged_results


async def normalize_qgraph(app: FastAPI, qgraph: QueryGraph) -> QueryGraph:
    """
    Given a TRAPI query graph creates a normalized query graph
    with primary curies replacing nonprimary ones
    """
    merged_nodes = {}

    node_code_map: Dict[str, Union[str, List]] = {}

    for node_code, node in qgraph.nodes.items():

        merged_nodes[node_code] = node.dict()

        # node.id can be none, a string, or a list
        if not node.id:
            # do nothing
            continue
        elif isinstance(node.id, list):
            equivalent_curies = await get_normalized_nodes(app, node.id)
            primary_ids = set()
            for nid in node.id:
                if equivalent_curies[nid.__root__]:
                    primary_ids.add(equivalent_curies[nid.__root__]['id']['identifier'])
                else:
                    primary_ids.add(nid)
            merged_nodes[node_code]['id'] = list(primary_ids)
            node_code_map[node_code] = list(primary_ids)
        else:
            equivalent_curies = await get_equivalent_curies(app, node.id)
            if equivalent_curies[node.id.__root__]:
                primary_id = equivalent_curies[node.id.__root__]['id']['identifier']
                merged_nodes[node_code]['id'] = primary_id
                node_code_map[node_code] = primary_id

    return QueryGraph.parse_obj({
        'nodes': merged_nodes,
        'edges': qgraph.edges
    })


async def normalize_kgraph(
        app: FastAPI,
        kgraph: KnowledgeGraph
) -> Tuple[KnowledgeGraph, Dict[str,str], Dict[str,str]]:
    """
    Given a TRAPI knowledge graph creates a merged graph
    by iterating over each node, getting the primary id,
    and merging nodes and edges (as needed)

    Returns a tuple with the first element being the merged
    knowledge graph, and the second element being a map
    of the original node id to the updated node id, and the third
    being an edge id map
    """

    merged_kgraph: Dict = {
        'nodes': {},
        'edges': {}
    }
    
    # Map for each node id (curie) and its primary id
    node_id_map: Dict[str, str] = {}

    # Map for each edge id and its primary id
    edge_id_map: Dict[str,str] = {}

    # Map for each edge to its s,p,r,o signature
    primary_edges: Dict[Tuple[str, str, str, str], str] = {}

    # cache for primary node ids
    primary_nodes_seen = set()

    # cache for nodes
    nodes_seen = set()

    # cache for subject, predicate, relation, object tuples
    edges_seen: Set[Tuple[str, str, str, str]] = set()

    for node_id, node in kgraph.nodes.items():
        if node_id in nodes_seen:
            continue

        nodes_seen.add(node_id)
        node_id_map[node_id] = node_id  # expected to overridden by primary id

        merged_node = node.dict()

        equivalent_curies = await get_equivalent_curies(app, node_id)

        if equivalent_curies[node_id]:
            primary_id = equivalent_curies[node_id]['id']['identifier']
            node_id_map[node_id] = primary_id

            if primary_id in primary_nodes_seen:
                # TODO attribute merging
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
        # TODO, there's ambiguous criteria for when to
        # merge an edge, for example
        # initial criteria: s,p,o or s,p,o,r
        # handling attributes if the above is met

        # Accessing __root__ directly seems wrong,
        # https://github.com/samuelcolvin/pydantic/issues/730
        # could also do str(edge.subject)
        if edge.subject.__root__ in node_id_map:
            primary_subject = node_id_map[edge.subject.__root__]
        else:
            # should we throw a validation error here?
            primary_subject = edge.subject

        if edge.object.__root__ in node_id_map:
            primary_object = node_id_map[edge.object.__root__]
        else:
            primary_object = edge.object

        triple = (
            primary_subject,
            edge.predicate.__root__,
            edge.relation,
            primary_object
        )
        if triple in edges_seen:
            edge_id_map[edge_id] = primary_edges[triple]
            continue
        else:
            primary_edges[triple] = edge_id
            edge_id_map[edge_id] = edge_id

        edges_seen.add(triple)
        merged_edge = edge.dict()

        merged_edge['subject'] = primary_subject
        merged_edge['object'] = primary_object
        merged_kgraph['edges'][edge_id] = merged_edge

    return KnowledgeGraph.parse_obj(merged_kgraph), node_id_map, edge_id_map


async def get_equivalent_curies(
        app: FastAPI,
        curie: Union[str, CURIE]
) -> Dict:
    """
    Get primary id and equivalent curies using redis GET

    Returns a dict with the structure
    {
      ${curie}:
        {'identifier': 'foo', 'label': bar},
        'equivalent_identifiers': [{'identifier': 'foo', 'label': bar}, ...],
        'type': ['named_thing']
    }
    """
    if isinstance(curie, CURIE):
        curie = curie.__root__
    default_return = {curie: None}
    # Get the equivalent list primary key identifier
    reference = await app.state.redis_connection0.get(curie, encoding='utf-8')
    if reference is None:
        return default_return
    value = await app.state.redis_connection1.get(reference, encoding='utf-8')
    return json.loads(value) if value is not None else default_return


async def get_normalized_nodes(
        app: FastAPI,
        curies: List[Union[CURIE, str]]
) -> Dict[str, Optional[str]]:
    """
    Get value(s) for key(s) using redis MGET
    """
    # malkovich malkovich
    curies = [
        curie.__root__ if isinstance(curie, CURIE) else curie
        for curie in curies
    ]
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
