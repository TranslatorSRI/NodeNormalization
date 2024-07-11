"""Test node_normalizer server.py"""
import json
import random

from node_normalizer.server import app
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from .helpers.redis_mocks import mock_get_equivalent_curies, mock_get_ic
from pathlib import Path
import os
from bmt import Toolkit


class MockRedis:
    def __init__(self, data):
        self.data = data

    async def mget(self, *args, **kwargs):
        return [self.data[x] if x in self.data else None for x in args]


# Id -> Canonical
app.state.eq_id_to_id_db = MockRedis(
    {"DOID:3812": "MONDO:0005002", "MONDO:0005002": "MONDO:0005002"}
)
# Canonical->Equiv
app.state.id_to_eqids_db = MockRedis(
    {"MONDO:0005002": json.dumps([{"i": "MONDO:0005002"}, {"i": "DOID:3812"}])}
)
app.state.id_to_type_db = MockRedis({"MONDO:0005002": "biolink:Disease"})
app.state.curie_to_bl_type_db = MockRedis({})
app.state.info_content_db = MockRedis({})
app.state.toolkit = Toolkit()
app.state.ancestor_map = {}

# TODO: add test for conflations.

def test_setid_empty():
    """
    Make sure we get a sensible response if we call setid without any parameters.
    """
    client = TestClient(app)
    response = client.get("/get_setid")
    result = response.json()
    assert result == {
        "detail":
            [
                {
                    "loc": ["query", "curie"],
                    "msg": "ensure this value has at least 1 items",
                    "type": "value_error.list.min_items",
                    "ctx": { "limit_value": 1 }
                }
            ]
    }


def test_setid_basic():
    """
    Some basic tests to make sure normalization works as expected.
    """
    client = TestClient(app)

    expected_setids = [
        {
            'curie': ['DOID:3812', 'MONDO:0005002', 'MONDO:0005003', ''],
            'normalized_curies': ['', 'MONDO:0005002', 'MONDO:0005003'],
            'normalized_string': '||MONDO:0005002||MONDO:0005003',
            'sha256hash': 'b0f633a8752fcf2bdfdeded274d39e99521b688964a2204308eb41ac4e55a922',
            'base64': 'fHxNT05ETzowMDA1MDAyfHxNT05ETzowMDA1MDAz',
            'base64zlib': 'eJyrqfH193PxtzIwMDA1MDCqQeEaAwCHqQgO'
        }
    ]

    for expected_setid in expected_setids:
        response = client.get("/get_setid", params={
            'curie': expected_setid['curie']
        })
        result = response.json()
        assert result['curies'] == expected_setid['curie']
        assert result['normalized_curies'] == expected_setid['normalized_curies']
        assert result['normalized_string'] == expected_setid['normalized_string']
        assert result['sha256hash'] == expected_setid['sha256hash']
        assert result['base64'] == expected_setid['base64']
        assert result['base64zlib'] == expected_setid['base64zlib']


def test_setid_long():
    """
    Some basic tests to make sure normalization of long lists of setid.
    """
    client = TestClient(app)

    # Generate up to a hundred rubbish IDs (between RUBBISH:10000 and RUBBISH:99999).
    # rubbish_ids = [f'RUBBISH:{random.randint(10000, 99999)}' for _ in range(100)]
    rubbish_ids = ["RUBBISH:47029", "RUBBISH:11782", "RUBBISH:19841", "RUBBISH:74772", "RUBBISH:50159", "RUBBISH:72510", "RUBBISH:71390", "RUBBISH:93274", "RUBBISH:54177", "RUBBISH:11018", "RUBBISH:75654", "RUBBISH:82342", "RUBBISH:58851", "RUBBISH:37847", "RUBBISH:39315", "RUBBISH:95403", "RUBBISH:87724", "RUBBISH:76080", "RUBBISH:62554", "RUBBISH:11207", "RUBBISH:24788", "RUBBISH:97930", "RUBBISH:98994", "RUBBISH:10111", "RUBBISH:46486", "RUBBISH:42114", "RUBBISH:97410", "RUBBISH:71911", "RUBBISH:10444", "RUBBISH:71057", "RUBBISH:16589", "RUBBISH:79128", "RUBBISH:32169", "RUBBISH:76813", "RUBBISH:13051", "RUBBISH:75665", "RUBBISH:33554", "RUBBISH:73285", "RUBBISH:79791", "RUBBISH:99397", "RUBBISH:36508", "RUBBISH:81324", "RUBBISH:27651", "RUBBISH:60525", "RUBBISH:13237", "RUBBISH:21080", "RUBBISH:21874", "RUBBISH:94750", "RUBBISH:95994", "RUBBISH:35060", "RUBBISH:15816", "RUBBISH:65196", "RUBBISH:74530", "RUBBISH:61006", "RUBBISH:97287", "RUBBISH:29972", "RUBBISH:36823", "RUBBISH:31799", "RUBBISH:68589", "RUBBISH:68594", "RUBBISH:63257", "RUBBISH:81351", "RUBBISH:38292", "RUBBISH:84666", "RUBBISH:50607", "RUBBISH:52926", "RUBBISH:48712", "RUBBISH:14093", "RUBBISH:88546", "RUBBISH:29904", "RUBBISH:75316", "RUBBISH:68679", "RUBBISH:99691", "RUBBISH:59711", "RUBBISH:57302", "RUBBISH:18425", "RUBBISH:71720", "RUBBISH:37939", "RUBBISH:23971", "RUBBISH:64822", "RUBBISH:69092", "RUBBISH:73348", "RUBBISH:56239", "RUBBISH:17439", "RUBBISH:80884", "RUBBISH:36822", "RUBBISH:11304", "RUBBISH:18228", "RUBBISH:59644", "RUBBISH:15815", "RUBBISH:93668", "RUBBISH:84725", "RUBBISH:40687", "RUBBISH:95196", "RUBBISH:12572", "RUBBISH:98753", "RUBBISH:52910", "RUBBISH:27338", "RUBBISH:28744", "RUBBISH:70919"]
    response = client.get("/get_setid", params={
        'curie': rubbish_ids
    })
    result = response.json()
    assert result['curies'] == rubbish_ids
    assert result['normalized_curies'] == [
        'RUBBISH:10111',
        'RUBBISH:10444',
        'RUBBISH:11018',
        'RUBBISH:11207',
        'RUBBISH:11304',
        'RUBBISH:11782',
        'RUBBISH:12572',
        'RUBBISH:13051',
        'RUBBISH:13237',
        'RUBBISH:14093',
        'RUBBISH:15815',
        'RUBBISH:15816',
        'RUBBISH:16589',
        'RUBBISH:17439',
        'RUBBISH:18228',
        'RUBBISH:18425',
        'RUBBISH:19841',
        'RUBBISH:21080',
        'RUBBISH:21874',
        'RUBBISH:23971',
        'RUBBISH:24788',
        'RUBBISH:27338',
        'RUBBISH:27651',
        'RUBBISH:28744',
        'RUBBISH:29904',
        'RUBBISH:29972',
        'RUBBISH:31799',
        'RUBBISH:32169',
        'RUBBISH:33554',
        'RUBBISH:35060',
        'RUBBISH:36508',
        'RUBBISH:36822',
        'RUBBISH:36823',
        'RUBBISH:37847',
        'RUBBISH:37939',
        'RUBBISH:38292',
        'RUBBISH:39315',
        'RUBBISH:40687',
        'RUBBISH:42114',
        'RUBBISH:46486',
        'RUBBISH:47029',
        'RUBBISH:48712',
        'RUBBISH:50159',
        'RUBBISH:50607',
        'RUBBISH:52910',
        'RUBBISH:52926',
        'RUBBISH:54177',
        'RUBBISH:56239',
        'RUBBISH:57302',
        'RUBBISH:58851',
        'RUBBISH:59644',
        'RUBBISH:59711',
        'RUBBISH:60525',
        'RUBBISH:61006',
        'RUBBISH:62554',
        'RUBBISH:63257',
        'RUBBISH:64822',
        'RUBBISH:65196',
        'RUBBISH:68589',
        'RUBBISH:68594',
        'RUBBISH:68679',
        'RUBBISH:69092',
        'RUBBISH:70919',
        'RUBBISH:71057',
        'RUBBISH:71390',
        'RUBBISH:71720',
        'RUBBISH:71911',
        'RUBBISH:72510',
        'RUBBISH:73285',
        'RUBBISH:73348',
        'RUBBISH:74530',
        'RUBBISH:74772',
        'RUBBISH:75316',
        'RUBBISH:75654',
        'RUBBISH:75665',
        'RUBBISH:76080',
        'RUBBISH:76813',
        'RUBBISH:79128',
        'RUBBISH:79791',
        'RUBBISH:80884',
        'RUBBISH:81324',
        'RUBBISH:81351',
        'RUBBISH:82342',
        'RUBBISH:84666',
        'RUBBISH:84725',
        'RUBBISH:87724',
        'RUBBISH:88546',
        'RUBBISH:93274',
        'RUBBISH:93668',
        'RUBBISH:94750',
        'RUBBISH:95196',
        'RUBBISH:95403',
        'RUBBISH:95994',
        'RUBBISH:97287',
        'RUBBISH:97410',
        'RUBBISH:97930',
        'RUBBISH:98753',
        'RUBBISH:98994',
        'RUBBISH:99397',
        'RUBBISH:99691'
    ]
    assert result['normalized_string'] == 'RUBBISH:10111||RUBBISH:10444||RUBBISH:11018||RUBBISH:11207||RUBBISH:11304||RUBBISH:11782||RUBBISH:12572||RUBBISH:13051||RUBBISH:13237||RUBBISH:14093||RUBBISH:15815||RUBBISH:15816||RUBBISH:16589||RUBBISH:17439||RUBBISH:18228||RUBBISH:18425||RUBBISH:19841||RUBBISH:21080||RUBBISH:21874||RUBBISH:23971||RUBBISH:24788||RUBBISH:27338||RUBBISH:27651||RUBBISH:28744||RUBBISH:29904||RUBBISH:29972||RUBBISH:31799||RUBBISH:32169||RUBBISH:33554||RUBBISH:35060||RUBBISH:36508||RUBBISH:36822||RUBBISH:36823||RUBBISH:37847||RUBBISH:37939||RUBBISH:38292||RUBBISH:39315||RUBBISH:40687||RUBBISH:42114||RUBBISH:46486||RUBBISH:47029||RUBBISH:48712||RUBBISH:50159||RUBBISH:50607||RUBBISH:52910||RUBBISH:52926||RUBBISH:54177||RUBBISH:56239||RUBBISH:57302||RUBBISH:58851||RUBBISH:59644||RUBBISH:59711||RUBBISH:60525||RUBBISH:61006||RUBBISH:62554||RUBBISH:63257||RUBBISH:64822||RUBBISH:65196||RUBBISH:68589||RUBBISH:68594||RUBBISH:68679||RUBBISH:69092||RUBBISH:70919||RUBBISH:71057||RUBBISH:71390||RUBBISH:71720||RUBBISH:71911||RUBBISH:72510||RUBBISH:73285||RUBBISH:73348||RUBBISH:74530||RUBBISH:74772||RUBBISH:75316||RUBBISH:75654||RUBBISH:75665||RUBBISH:76080||RUBBISH:76813||RUBBISH:79128||RUBBISH:79791||RUBBISH:80884||RUBBISH:81324||RUBBISH:81351||RUBBISH:82342||RUBBISH:84666||RUBBISH:84725||RUBBISH:87724||RUBBISH:88546||RUBBISH:93274||RUBBISH:93668||RUBBISH:94750||RUBBISH:95196||RUBBISH:95403||RUBBISH:95994||RUBBISH:97287||RUBBISH:97410||RUBBISH:97930||RUBBISH:98753||RUBBISH:98994||RUBBISH:99397||RUBBISH:99691'
    assert result['sha256hash'] == 'b88b6231c28345f85fcbed06b388180933bc53fc486289b5e7e1d3286bc6dd38'
    assert result['base64'] == 'UlVCQklTSDoxMDExMXx8UlVCQklTSDoxMDQ0NHx8UlVCQklTSDoxMTAxOHx8UlVCQklTSDoxMTIwN3x8UlVCQklTSDoxMTMwNHx8UlVCQklTSDoxMTc4Mnx8UlVCQklTSDoxMjU3Mnx8UlVCQklTSDoxMzA1MXx8UlVCQklTSDoxMzIzN3x8UlVCQklTSDoxNDA5M3x8UlVCQklTSDoxNTgxNXx8UlVCQklTSDoxNTgxNnx8UlVCQklTSDoxNjU4OXx8UlVCQklTSDoxNzQzOXx8UlVCQklTSDoxODIyOHx8UlVCQklTSDoxODQyNXx8UlVCQklTSDoxOTg0MXx8UlVCQklTSDoyMTA4MHx8UlVCQklTSDoyMTg3NHx8UlVCQklTSDoyMzk3MXx8UlVCQklTSDoyNDc4OHx8UlVCQklTSDoyNzMzOHx8UlVCQklTSDoyNzY1MXx8UlVCQklTSDoyODc0NHx8UlVCQklTSDoyOTkwNHx8UlVCQklTSDoyOTk3Mnx8UlVCQklTSDozMTc5OXx8UlVCQklTSDozMjE2OXx8UlVCQklTSDozMzU1NHx8UlVCQklTSDozNTA2MHx8UlVCQklTSDozNjUwOHx8UlVCQklTSDozNjgyMnx8UlVCQklTSDozNjgyM3x8UlVCQklTSDozNzg0N3x8UlVCQklTSDozNzkzOXx8UlVCQklTSDozODI5Mnx8UlVCQklTSDozOTMxNXx8UlVCQklTSDo0MDY4N3x8UlVCQklTSDo0MjExNHx8UlVCQklTSDo0NjQ4Nnx8UlVCQklTSDo0NzAyOXx8UlVCQklTSDo0ODcxMnx8UlVCQklTSDo1MDE1OXx8UlVCQklTSDo1MDYwN3x8UlVCQklTSDo1MjkxMHx8UlVCQklTSDo1MjkyNnx8UlVCQklTSDo1NDE3N3x8UlVCQklTSDo1NjIzOXx8UlVCQklTSDo1NzMwMnx8UlVCQklTSDo1ODg1MXx8UlVCQklTSDo1OTY0NHx8UlVCQklTSDo1OTcxMXx8UlVCQklTSDo2MDUyNXx8UlVCQklTSDo2MTAwNnx8UlVCQklTSDo2MjU1NHx8UlVCQklTSDo2MzI1N3x8UlVCQklTSDo2NDgyMnx8UlVCQklTSDo2NTE5Nnx8UlVCQklTSDo2ODU4OXx8UlVCQklTSDo2ODU5NHx8UlVCQklTSDo2ODY3OXx8UlVCQklTSDo2OTA5Mnx8UlVCQklTSDo3MDkxOXx8UlVCQklTSDo3MTA1N3x8UlVCQklTSDo3MTM5MHx8UlVCQklTSDo3MTcyMHx8UlVCQklTSDo3MTkxMXx8UlVCQklTSDo3MjUxMHx8UlVCQklTSDo3MzI4NXx8UlVCQklTSDo3MzM0OHx8UlVCQklTSDo3NDUzMHx8UlVCQklTSDo3NDc3Mnx8UlVCQklTSDo3NTMxNnx8UlVCQklTSDo3NTY1NHx8UlVCQklTSDo3NTY2NXx8UlVCQklTSDo3NjA4MHx8UlVCQklTSDo3NjgxM3x8UlVCQklTSDo3OTEyOHx8UlVCQklTSDo3OTc5MXx8UlVCQklTSDo4MDg4NHx8UlVCQklTSDo4MTMyNHx8UlVCQklTSDo4MTM1MXx8UlVCQklTSDo4MjM0Mnx8UlVCQklTSDo4NDY2Nnx8UlVCQklTSDo4NDcyNXx8UlVCQklTSDo4NzcyNHx8UlVCQklTSDo4ODU0Nnx8UlVCQklTSDo5MzI3NHx8UlVCQklTSDo5MzY2OHx8UlVCQklTSDo5NDc1MHx8UlVCQklTSDo5NTE5Nnx8UlVCQklTSDo5NTQwM3x8UlVCQklTSDo5NTk5NHx8UlVCQklTSDo5NzI4N3x8UlVCQklTSDo5NzQxMHx8UlVCQklTSDo5NzkzMHx8UlVCQklTSDo5ODc1M3x8UlVCQklTSDo5ODk5NHx8UlVCQklTSDo5OTM5N3x8UlVCQklTSDo5OTY5MQ=='
    assert result['base64zlib'] == 'eJxVlDl2GEEIBa/EvihUZKfy8210eBNZ1WFN07+BD/P19/Pz959fHyqq+v399R8jAnjHQzRpossT3GNAyya6JB9yc0qFrANzNF8sYOUssMOJY8acJ4xSO4E0TGWEOI2KzLcZHD1QtnZ/sFignRKlduVFNse1FyW4aRE9E3c9pZCzV8oQr/4X0VjviSYuW+djy7vrdCGkBnfDVJFVVAw8ihaDckwrlFM0l1icq7RVedCgnKHN4DKWkO3Ch2ZoSm7RlDx7cVqSHJVSEbxb9rhQfvMNjKftNwrLu/NM7OFSaqp5ukIXWlZx2ip8t9VXiG0PLgtsSza23SaJHhikjnQGR3NiO50r2VlszmFRuZ4t6xrFTPYqF7b3PvzgyAyU76a9SH9v1gNJTlQVsenvXEGUmgwErxt/BetVSHKjExXta/dmiBOXdt/mc4+2g6Zc9Wz7znWa+Erd+lJqa/UffQarTA=='
