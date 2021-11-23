import json
from typing import List, Dict, Optional, Any, Set, Tuple, Union
import uuid
from uuid import UUID
from .util import LoggingUtil, uniquify_list
import logging
import os
from fastapi import FastAPI
from reasoner_pydantic import KnowledgeGraph, Message, QueryGraph, Result, CURIE, Attribute

logger = LoggingUtil.init_logging(__name__, level=logging.INFO, format='medium', logFilePath=os.path.dirname(__file__), logFileLevel=logging.INFO)


def get_ancestors(app, input_type):
    if input_type in app.state.ancestor_map:
        return app.state.ancestor_map[input_type]
    a = app.state.toolkit.get_ancestors(input_type)
    ancs = [app.state.toolkit.get_element(ai)['class_uri'] for ai in a]
    if input_type not in ancs:
        ancs = [input_type] + ancs
    app.state.ancestor_map[input_type] = ancs
    return ancs


async def normalize_message(app: FastAPI, message: Message) -> Message:
    """
    Given a TRAPI message, updates the message to include a
    normalized qgraph, kgraph, and results
    """
    try:
        merged_qgraph = await normalize_qgraph(app, message.query_graph)
        merged_kgraph, node_id_map, edge_id_map = await normalize_kgraph(app, message.knowledge_graph)
        merged_results = await normalize_results(app, message.results, node_id_map, edge_id_map)

        return Message.parse_obj({
            'query_graph': merged_qgraph,
            'knowledge_graph': merged_kgraph,
            'results': merged_results
        })
    except Exception as e:
        logger.error(f'normalize_message Exception: {e}')


async def normalize_results(app,
        results: List[Result],
        node_id_map: Dict[str, str],
        edge_id_map: Dict[str, str]
) -> List[Result]:
    """
    Given a TRAPI result creates a normalized result object
    """

    merged_results: List[Result] = []
    result_seen = set()

    for result in results:
        merged_result = {
            'node_bindings': {},
            'edge_bindings': {}
        }

        try:
            node_binding_seen = set()
            edge_binding_seen = set()

            for node_code, node_bindings in result.node_bindings.items():
                merged_node_bindings = []
                for n_bind in node_bindings:
                    merged_binding = n_bind.dict()
                    merged_binding['id'] = node_id_map[n_bind.id.__root__]

                    # get the information content value
                    ic_attrib = await get_info_content_attribute(app, merged_binding['id'])

                    # did we get a good attribute dict
                    if ic_attrib:
                        if 'attributes' in merged_binding:
                            merged_binding['attributes'].append(ic_attrib)
                        else:
                            merged_binding['attributes'] = [ic_attrib]

                    node_binding_information = [
                        "atts" if k == 'attributes'
                        else (k, tuple(v)) if isinstance(v, list)
                        else (k, v)
                        for k, v in merged_binding.items()
                    ]

                    # if there are attributes in the node binding
                    if 'attributes' in merged_binding:
                        # storage for the pydantic Attributes
                        attribs = []

                        # the items in list of attributes must be of type Attribute
                        # in order to reuse hash method
                        for attrib in merged_binding['attributes']:
                            new_attrib = Attribute.parse_obj(attrib)

                            # add the new Attribute to the list
                            attribs.append(new_attrib)

                        # call to get the hash
                        atty_hash = _hash_attributes(attribs)
                        node_binding_information.append(atty_hash)
                    node_binding_hash = frozenset(node_binding_information)

                    if node_binding_hash in node_binding_seen:
                        continue
                    else:
                        node_binding_seen.add(node_binding_hash)
                        merged_node_bindings.append(merged_binding)

                merged_result['node_bindings'][node_code] = merged_node_bindings

            for edge_code, edge_bindings in result.edge_bindings.items():
                merged_edge_bindings = []
                for e_bind in edge_bindings:
                    merged_binding = e_bind.dict()
                    merged_binding['id'] = edge_id_map[e_bind.id]

                    edge_binding_hash = frozenset([
                        (k, tuple(v))
                        if isinstance(v, list)
                        else (k, v)
                        for k, v in merged_binding.items()
                    ])

                    if edge_binding_hash in edge_binding_seen:
                        continue
                    else:
                        edge_binding_seen.add(edge_binding_hash)
                        merged_edge_bindings.append(merged_binding)

                merged_result['edge_bindings'][edge_code] = merged_edge_bindings

            try:
                # This used to have some list comprehension based on types.  But in TRAPI 1.1 the list/dicts get pretty deep.
                # This is simpler, and the sort_keys argument makes sure we get a constant result.
                hashed_result = json.dumps(merged_result, sort_keys=True)

            except Exception as e:  # TODO determine exception(s) to catch
                logger.error(f'normalize_results Exception: {e}')
                hashed_result = False

            if hashed_result is not False:
                if hashed_result in result_seen:
                    continue
                else:
                    result_seen.add(hashed_result)

            merged_results.append(Result.parse_obj(merged_result))
        except Exception as e:
            logger.error(f'normalize_results Exception: {e}')

    return merged_results


async def normalize_qgraph(app: FastAPI, qgraph: QueryGraph) -> QueryGraph:
    """
    Given a TRAPI query graph creates a normalized query graph
    with primary curies replacing nonprimary ones
    """
    merged_nodes = {}

    node_code_map: Dict[str, Union[str, List]] = {}

    for node_code, node in qgraph.nodes.items():
        try:
            merged_nodes[node_code] = node.dict()

            # as of TRAPI 1.1, node.id must be none or a list.
            # node.id can be none, a string, or a list
            if not node.ids:
                # do nothing
                continue
            else:
                if not isinstance(node.ids, list):
                    raise Exception("node.ids must be a list")
                primary_ids = set()
                for nid in node.ids:
                    nr = nid.__root__
                    equivalent_curies = await get_equivalent_curies(app, nr)
                    if equivalent_curies[nr]:
                        primary_ids.add(equivalent_curies[nr]['id']['identifier'])
                    else:
                        primary_ids.add(nr)
                merged_nodes[node_code]['ids'] = list(primary_ids)
                node_code_map[node_code] = list(primary_ids)
        except Exception as e:
            logger.error(f'normalize_qgraph Exception: {e}')

    return QueryGraph.parse_obj({
        'nodes': merged_nodes,
        'edges': qgraph.edges
    })


async def normalize_kgraph(
        app: FastAPI,
        kgraph: KnowledgeGraph
) -> Tuple[KnowledgeGraph, Dict[str, str], Dict[str, str]]:
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

    node_id_map: Dict[str, str] = {}
    edge_id_map: Dict[str, str] = {}

    try:
        # Map for each node id (curie) and its primary id
        node_id_map: Dict[str, str] = {}

        # Map for each edge id and its primary id
        edge_id_map: Dict[str, str] = {}

        # Map for each edge to its s,p,r,o signature
        primary_edges: Dict[Tuple[str, str, Optional[str], str, Union[UUID, int]], str] = {}

        # cache for primary node ids
        primary_nodes_seen = set()

        # Count of times a node has been merged for attribute merging
        node_merge_count: Dict[str, int] = {}

        # cache for nodes
        nodes_seen = set()

        # cache for subject, predicate, relation, object, attribute hash tuples
        edges_seen: Set[Tuple[str, str, str, str, Union[UUID, int]]] = set()

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
                    merged_node = _merge_node_attributes(
                        node_a=merged_kgraph['nodes'][primary_id],
                        node_b=node.dict(),
                        merged_count=node_merge_count[primary_id]
                    )
                    merged_kgraph['nodes'][primary_id] = merged_node
                    node_merge_count[primary_id] += 1
                    continue
                else:
                    node_merge_count[primary_id] = 0

                primary_nodes_seen.add(primary_id)

                if 'label' in equivalent_curies[node_id]['id']:
                    primary_label = equivalent_curies[node_id]['id']['label']
                elif 'name' in merged_node:
                    primary_label = merged_node['name']
                else:
                    primary_label = ''

                merged_node['name'] = primary_label

                # Even if there's already a same_as attribute we add another
                # since it is coming from a new source
                if 'equivalent_identifiers' in equivalent_curies[node_id]:
                    same_as_attribute = {
                        'attribute_type_id': 'biolink:same_as',
                        'value': [
                            node['identifier']
                            for node in equivalent_curies[node_id]['equivalent_identifiers']
                        ],
                        'original_attribute_name': 'equivalent_identifiers',
                        "value_type_id": "EDAM:data_0006",

                        # TODO, should we add the app version as the source
                        # or perhaps the babel/redis cache version
                        # This will make unit testing a little more tricky
                        # see https://stackoverflow.com/q/57624731

                        # 'source': f'{app.title} {app.version}',
                    }
                    if 'attributes' in merged_node and merged_node['attributes']:
                        merged_node['attributes'].append(same_as_attribute)
                    else:
                        merged_node['attributes'] = [same_as_attribute]

                if 'type' in equivalent_curies[node_id]:
                    if type(equivalent_curies[node_id]['type']) is list:
                        merged_node['categories'] = equivalent_curies[node_id]['type']
                    else:
                        merged_node['categories'] = [equivalent_curies[node_id]['type']]

                # get the information content value
                ic_attrib = await get_info_content_attribute(app, node_id)

                # did we get a good attribute dict
                if ic_attrib:
                    # add the attribute to the node
                    merged_node['attributes'].append(ic_attrib)

                merged_kgraph['nodes'][primary_id] = merged_node
            else:
                merged_kgraph['nodes'][node_id] = merged_node

        for edge_id, edge in kgraph.edges.items():
            # Accessing __root__ directly seems wrong,
            # https://github.com/samuelcolvin/pydantic/issues/730
            # could also do str(edge.subject)
            if edge.subject.__root__ in node_id_map:
                primary_subject = node_id_map[edge.subject.__root__]
            else:
                # should we throw a validation error here?
                primary_subject = edge.subject.__root__

            if edge.object.__root__ in node_id_map:
                primary_object = node_id_map[edge.object.__root__]
            else:
                primary_object = edge.object.__root__

            hashed_attributes = _hash_attributes(edge.attributes)

            if hashed_attributes is False:
                # we couldn't hash the attribute so assume unique
                hashed_attributes = uuid.uuid4()

            triple = (
                primary_subject,
                edge.predicate.__root__,
                primary_object,
                hashed_attributes
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
    except Exception as e:
        logger.error(f'normalize_kgraph Exception: {e}')

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

    # set default return in case curie not found
    default_return = {curie: None}

    try:

        # Get the equivalent list primary key identifier
        value = await get_normalized_nodes(app, [curie], True)

        # did we get a valid response
        if value is None:
            # no, so return the default
            return default_return

    except Exception as e:
        logger.error(f'get_equivalent_curies Exception: {e}')
        return default_return

    # return the curie normalization data
    return value


async def get_info_content(
        app: FastAPI,
        canonical_nonan: List) -> dict:
    """
    Gets the information content value for the node id

    :param app:
    :param canonical_nonan:
    :return:
    """
    # call redis and get the value
    info_contents = await app.state.redis_connection4.mget(*canonical_nonan, encoding='utf8')

    # get this into a list
    info_contents = [round(float(ic_ids), 1) if ic_ids is not None else None for ic_ids in info_contents]

    # zip into an array of dicts
    info_contents = dict(zip(canonical_nonan, info_contents))

    # return the value to the caller
    return info_contents


async def get_eqids_and_types(
        app: FastAPI,
        canonical_nonan: List) -> (List, List):
    if len(canonical_nonan) == 0:
        return [], []
    eqids = await app.state.redis_connection1.mget(*canonical_nonan, encoding='utf-8')
    eqids = [json.loads(value) if value is not None else None for value in eqids]
    types = await app.state.redis_connection2.mget(*canonical_nonan, encoding='utf-8')
    types = [get_ancestors(app, t) for t in types]
    return eqids, types


async def get_normalized_nodes(
        app: FastAPI,
        curies: List[Union[CURIE, str]],
        conflate: bool
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

    # TODO: Add an option that lets one choose which conflations to do, and get the details of those conflations from the configs.
    # conflation_types = {"biolink:Gene", "biolink:Protein"}
    # conflation_redis = 5

    upper_curies = [c.upper() for c in curies]
    try:
        canonical_ids = await app.state.redis_connection0.mget(*upper_curies, encoding='utf-8')
        canonical_nonan = [canonical_id for canonical_id in canonical_ids if canonical_id is not None]

        # did we get some canonical ids
        if canonical_nonan:
            # Get the equivalent_ids and types
            eqids, types = await get_eqids_and_types(app, canonical_nonan)

            # get the information content values
            info_contents = await get_info_content(app, canonical_nonan)

            # are we looking for conflated values
            if conflate:
                # TODO: filter to just types that have Gene or Protein?  I'm not sure it's worth it when we have pipelining
                other_ids = await app.state.redis_connection5.mget(*canonical_nonan, encoding='utf8')

                # if there are other ids, then we want to rebuild eqids and types.  That's because even though we have them,
                # they're not necessarily first.  For instance if what came in and got canonicalized was a protein id
                # and we want gene first, then we're relying on the order of the other_ids to put it back in the right place.
                other_ids = [json.loads(oids) if oids is not None else [] for oids in other_ids]
                dereference_others = dict(zip(canonical_nonan, other_ids))

                all_other_ids = sum(other_ids, [])
                eqids2, types2 = await get_eqids_and_types(app, all_other_ids)

                final_eqids = []
                final_types = []

                deref_others_eqs = dict(zip(all_other_ids, eqids2))
                deref_others_typ = dict(zip(all_other_ids, types2))

                zipped = zip(canonical_nonan, eqids, types)

                for canonical_id, e, t in zipped:
                    # here's where we replace the eqids, types
                    if len(dereference_others[canonical_id]) > 0:
                        e = []
                        t = []

                    for other in dereference_others[canonical_id]:
                        e += deref_others_eqs[other]
                        t += deref_others_typ[other]

                    final_eqids.append(e)
                    final_types.append(uniquify_list(t))

                dereference_ids = dict(zip(canonical_nonan, final_eqids))
                dereference_types = dict(zip(canonical_nonan, final_types))
            else:
                dereference_ids = dict(zip(canonical_nonan, eqids))
                dereference_types = dict(zip(canonical_nonan, types))
        else:
            dereference_ids = dict()
            dereference_types = dict()

        # output the final result
        normal_nodes = {
            input_curie: await create_node(canonical_id, dereference_ids, dereference_types, info_contents)
            for input_curie, canonical_id, info_content in zip(curies, canonical_ids, info_contents)
        }

    except Exception as e:
        logger.error(f'Exception: {e}')

    return normal_nodes


async def get_info_content_attribute(app, canonical_nonan) -> dict:
    """
    gets the information content value from the redis cache

    :param app:
    :param canonical_nonan:
    :return:
    """
    # get the information content value
    ic_val = await app.state.redis_connection4.get(canonical_nonan, encoding='utf8')

    # did we get a good value
    if ic_val is not None:
        # load up a dict with the attribute data and create a trapi attribute object
        new_attrib = dict(attribute_type_id="biolink:has_numeric_value", original_attribute_name="information_content", value_type_id="EDAM:data_0006", value=round(float(ic_val), 1))
    else:
        # else return nothing
        new_attrib = None

    # return to the caller
    return new_attrib

async def create_node(canonical_id, equivalent_ids, types, info_contents):
    """Construct the output format given the compressed redis data"""
    # It's possible that we didn't find a canonical_id
    if canonical_id is None:
        return None

    # OK, now we should have id's in the format [ {"i": "MONDO:12312", "l": "Scrofula"}, {},...]
    eids = equivalent_ids[canonical_id]

    # First, we need to create the "id" node.  The identifier is our input canonical id, but we have to get a label
    labels = list(filter(lambda x: len(x) > 0, [eid['l'] for eid in eids if 'l' in eid]))

    # Note that the id will be from the equivalent ids, not the canonical_id.  This is to handle conflation
    if len(labels) > 0:
        node = {"id": {"identifier": eids[0]['i'], "label": labels[0]}}
    else:
        # Sometimes, nothing has a label :(
        node = {"id": {"identifier": eids[0]['i']}}

    # now need to reformat the identifier keys.  It could be cleaner but we have to worry about if there is a label
    node['equivalent_identifiers'] = [{"identifier": eqid["i"], "label": eqid["l"]} if "l" in eqid
                                      else {"identifier": eqid["i"]} for eqid in eids]

    node['type'] = types[canonical_id]

    # add the info content to the node if we got one
    if info_contents[canonical_id] is not None:
        node['information_content'] = info_contents[canonical_id]

    return node


async def get_curie_prefixes(
        app: FastAPI,
        semantic_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get pivot table of semantic type x curie prefix
    """
    ret_val: dict = {}  # storage for the returned data

    try:
        # was an arg passed in
        if semantic_types:
            for item in semantic_types:
                # get the curies for this type
                curies = await app.state.redis_connection3.get(item, encoding='utf-8')

                # did we get any data
                if not curies:
                    curies = '{' + f'"{item}"' + ': "Not found"}'

                curies = json.loads(curies)

                # set the return data
                ret_val[item] = {'curie_prefix': curies}
        else:
            types = await app.state.redis_connection3.lrange('semantic_types', 0, -1, encoding='utf-8')

            for item in types:
                # get the curies for this type
                curies = await app.state.redis_connection3.get(item, encoding='utf-8')

                # did we get any data
                if not curies:
                    curies = '{' + f'"{item}"' + ': "Not found"}'

                curies = json.loads(curies)

                # set the return data
                ret_val[item] = {'curie_prefix': curies}
    except Exception as e:
        logger.error(f'get_curie_prefixes Exception: {e}')

    return ret_val


def _merge_node_attributes(node_a: Dict, node_b, merged_count: int) -> Dict:
    """
    :param node_a: the primary node
    :param node_b: the node to be merged
    :param merged_count: the number of nodes merged into node_a **upon entering this fx**
    """

    try:
        if not ('attributes' in node_b and node_b['attributes']):
            return node_a

        if merged_count == 0:
            if 'attributes' in node_a and node_a['attributes']:
                new_attribute_list = []
                for attribute in node_a['attributes']:
                    new_dict = {}
                    for k, v in attribute.items():
                        new_dict[f"{k}.1"] = v
                    new_attribute_list.append(new_dict)

                node_a['attributes'] = new_attribute_list

        # Need to DRY this off
        b_attr_id = merged_count + 2
        if 'attributes' in node_b and node_b['attributes']:
            new_attribute_list = []
            for attribute in node_b['attributes']:
                new_dict = {}
                for k, v in attribute.items():
                    new_dict[f"{k}.{b_attr_id}"] = v
                new_attribute_list.append(new_dict)

            node_a['attributes'] = node_a['attributes'] + new_attribute_list
    except Exception as e:
        logger.error(f'_merge_node_attributes Exception {e}')

    return node_a


def _hash_attributes(attributes: List[Attribute] = None) -> Union[int, bool]:
    """
    Attempt to make an attribute list hashable by converting it to a
    tuple of tuples

    Using the python builtin hash https://docs.python.org/3.5/library/functions.html#hash
    Which can technically return zero, so downstream code should explicitly check
    for a False value instead of falsy values

    The tricky thing here is that attribute.value is an Any type, so we do some type
    checking to see if it's hashable
    """
    new_attributes = []

    try:
        if not attributes:
            return hash(attributes)

        for attribute in attributes:
            hashed_value = attribute.value
            if attribute.value:
                if isinstance(attribute.value, list):
                    # TODO list of lists?
                    hashed_value = tuple(attribute.value)
                elif isinstance(attribute.value, dict):
                    hashed_value = tuple(
                        (k, tuple(v))
                        if isinstance(v, list)
                        else (k, v)
                        for k, v in attribute.value.items())

            new_attribute = (
                attribute.attribute_type_id.__root__,
                hashed_value,
                attribute.original_attribute_name,
                attribute.value_url,
                attribute.attribute_source,
                attribute.value_type_id.__root__ if attribute.value_type_id is not None else '',
                attribute.attribute_source
            )
            new_attributes.append(new_attribute)

        return hash(frozenset(new_attributes))
    except Exception as e:
        logger.error(f'_hash_attributes Exception: {e}')
        return False
