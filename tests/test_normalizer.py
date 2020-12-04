"""Test node_normalizer normalizer.py"""
import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from reasoner_pydantic import KnowledgeGraph

from tests.redis_mocks import mock_get_equivalent_curies
from node_normalizer.normalizer import normalize_kgraph


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

        postmerged_from_api = await normalize_kgraph(app, premerged_data)

        # dictionary equality might be brittle
        assert postmerged_from_api.dict() == postmerged_from_file
