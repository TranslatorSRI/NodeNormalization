"""Test node_normalizer normalizer.py"""
import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from reasoner_pydantic import Attribute, CURIE


from reasoner_pydantic import KnowledgeGraph
# Need to add to sources root to avoid linter warnings
from redis_mocks import mock_get_equivalent_curies
from node_normalizer.normalizer import normalize_kgraph, _hash_attributes, _merge_node_attributes


premerged_graph = Path(__file__).parent / 'resources' / 'premerged_kgraph.json'
postmerged_graph = Path(__file__).parent / 'resources' / 'postmerged_kgraph.json'


class TestNormalizer:

    @pytest.mark.asyncio
    @patch('node_normalizer.normalizer.get_equivalent_curies', Mock(side_effect=mock_get_equivalent_curies))
    async def test_kg_normalize(self):
        app = None
        with open(premerged_graph, 'r') as pre:
            premerged_data = KnowledgeGraph.parse_obj(json.load(pre))

        with open(postmerged_graph, 'r') as post:
            postmerged_from_file = json.load(post)

        postmerged_from_api, nmap, emap = await normalize_kgraph(app, premerged_data)

        # dictionary equality might be brittle
        assert postmerged_from_api.dict() == postmerged_from_file

    def test_hashable_attribute(self):
        # value is a scalar
        hashable_attribute = Attribute(
            type=CURIE.parse_obj("foo:bar"),
            value=3,
            name='test',
            source='test_source'
        )
        assert _hash_attributes([hashable_attribute]) is not False

        # value is None
        hashable_attribute = Attribute(
            type=CURIE.parse_obj("foo:bar"),
            value=None,
            name='test',
            source='test_source'
        )
        assert _hash_attributes([hashable_attribute]) is not False

        # value is a list
        hashable_attribute = Attribute(
            type=CURIE.parse_obj("foo:bar"),
            value=[1,2,3],
            name='test',
            source='test_source'
        )

        assert _hash_attributes([hashable_attribute]) is not False

        # value is a dict of scalars/lists
        hashable_attribute = Attribute(
            type=CURIE.parse_obj("foo:bar"),
            value={1:2, 3:[4,5]},
            name='test',
            source='test_source'
        )

        assert _hash_attributes([hashable_attribute]) is not False

        # None check
        assert _hash_attributes(None) is not False
        assert _hash_attributes(None) == _hash_attributes(None)

        # Sanity checks
        assert _hash_attributes([Attribute(type=CURIE.parse_obj("foo:bar"), value=1)]) == \
               _hash_attributes([Attribute(type=CURIE.parse_obj("foo:bar"), value=1)])

        assert _hash_attributes([Attribute(type=CURIE.parse_obj("foo:bar"), value=1)]) != \
               _hash_attributes([Attribute(type=CURIE.parse_obj("foo:bar"), value=2)])

    def test_unhashable_attribute(self):
        # value is a nested dict
        hashable_attribute = Attribute(
            type=CURIE.parse_obj("foo:bar"),
            value={1:{2:3}},
            name='test',
            source='test_source'
        )
        assert _hash_attributes([hashable_attribute]) is False

    def test_merge_node_attributes(self):
        node_a = {
            'id': 'primary:id',
            'attributes': [
                {
                    'type': 'bar:baz',
                    'value': 1
                }
            ]
        }

        node_b = {
            'id': 'secondary:id',
            'attributes': [
                {
                    'type': 'bar:baz',
                    'value': 2
                }
            ]
        }
        new_node = _merge_node_attributes(node_a, node_b, 0)
        assert new_node == {
            'id': 'primary:id',
            'attributes': [
                {
                    'type.1': 'bar:baz',
                    'value.1': 1
                },
                {
                    'type.2': 'bar:baz',
                    'value.2': 2
                }
            ]
        }

        node_a = {
            'id': 'primary:id',
            'attributes': [
                {
                    'type.1': 'bar:baz',
                    'value.1': 1
                }
            ]
        }

        new_node = _merge_node_attributes(node_a, node_b, 1)
        assert new_node == {
            'id': 'primary:id',
            'attributes': [
                {
                    'type.1': 'bar:baz',
                    'value.1': 1
                },
                {
                    'type.3': 'bar:baz',
                    'value.3': 2
                }
            ]
        }
