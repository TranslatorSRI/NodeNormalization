"""Test node_normalizer server.py"""
from deepdiff import DeepDiff
import json
import time

import reasoner_pydantic
import requests
from pathlib import Path

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def test_get_conflations(session):
    host_url = "http://127.0.0.1:8080/get_allowed_conflations"
    print(f"host_url: {host_url}")
    response = requests.get(url=host_url, headers=HEADERS)
    print(f"{response.text}")
    assert response.status_code == 200


def test_async_query_callback(session):
    host_url = "http://127.0.0.1:8080/asyncquery"
    print(f"host_url: {host_url}")

    callback_url = f"http://callback-app:8008/receive_callback_query"
    print(f"callback_url: {callback_url}")

    basic_query_file = Path(__file__).parent / "resources" / "basic_query.json"

    with open(basic_query_file, "r") as pre:
        basic_query_data = json.load(pre)

    basic_query_data["callback"] = callback_url

    async_query = reasoner_pydantic.message.AsyncQuery.parse_obj(basic_query_data)

    response = requests.post(url=host_url, headers=HEADERS, data=async_query.json())

    # sleep here to allow the /asyncquery background task to run through
    time.sleep(10)

    assert response.status_code == 200
    assert response.json() == {"description": f"Query commenced. Will send result to {callback_url}"}

    compose_stdout, compose_stderr = session[0].get_logs()
    assert b'Successfully received message from "http://callback-app:8008/receive_callback_query"' in compose_stdout


def test_message_normalize_endpoint(session):
    host_url = "http://127.0.0.1:8080/query"
    print(f"host_url: {host_url}")

    basic_query_file = Path(__file__).parent / "resources" / "basic_query.json"
    with open(basic_query_file, "r") as pre:
        basic_query = json.load(pre)

    query = reasoner_pydantic.message.Query.parse_obj(basic_query)

    response = requests.post(url=host_url, headers=HEADERS, data=query.json())
    assert response.status_code == 200
    response_json = response.json()

    # confirm that the used, non-canonical identifier is replaced with the canonical identifier
    assert (
        response_json["message"]["query_graph"]["nodes"]["n1"]["ids"][0] == "NCBIGene:64109"
        and response_json["message"]["query_graph"]["nodes"]["n1"]["ids"][0] != "HGNC:14281"
    )
    assert (
        response_json["message"]["query_graph"]["nodes"]["n2"]["ids"][0] == "MONDO:0013985"
        and response_json["message"]["query_graph"]["nodes"]["n2"]["ids"][0] != "DOID:0110474"
    )


def test_get_semantic_types(session):
    host_url = "http://127.0.0.1:8080/get_semantic_types"
    response = requests.get(url=host_url, headers=HEADERS)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["semantic_types"] is not None
    # this is utterly idiotic...no idiomatic list contains list?  There has to be a better way to do this.
    assert all(elem in response_json["semantic_types"]["types"] for elem in ["biolink:Disease", "biolink:Gene", "biolink:Cell", "biolink:Protein"])


def test_get_normalized_nodes_not_found(session):
    host_url = "http://127.0.0.1:8080/get_normalized_nodes"

    # GET
    response = requests.get(url=host_url, headers=HEADERS, params={"curie": ["UNKNOWN:000000"]})
    assert response.status_code == 200
    response_json = response.json()
    assert response_json == {"UNKNOWN:000000": None}

    # POST
    response = requests.post(url=host_url, headers=HEADERS, json={"curies": ["UNKNOWN:000000"]})
    assert response.status_code == 200
    response_json = response.json()
    assert response_json == {"UNKNOWN:000000": None}


def test_get_normalized_nodes_one_missing():
    host_url = "http://127.0.0.1:8080/get_normalized_nodes"

    response = requests.get(url=host_url, headers=HEADERS, params={"curie": ["UNKNOWN:000000", "DOID:0110474"]})
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 2
    assert not response_json["UNKNOWN:000000"]
    assert response_json["DOID:0110474"]["id"]["identifier"] == "MONDO:0013985"


def test_get_normalized_nodes_all_missing():
    """
    /get_normalized_nodes previously returned {} if none of the provided CURIEs are resolvable.
    This test ensures that that bug has been fixed.

    Reported in https://github.com/TranslatorSRI/NodeNormalization/issues/113
    """

    host_url = "http://127.0.0.1:8080/get_normalized_nodes"

    # GET
    response = requests.get(url=host_url, headers=HEADERS, params={"curie": ["NCBIGene:ABCD", "NCBIGene:GENE:1017"]})
    assert response.status_code == 200
    response_json = response.json()
    assert response_json == {"NCBIGene:ABCD": None, "NCBIGene:GENE:1017": None}

    # POST
    response = requests.post(url=host_url, headers=HEADERS, json={"curies": ["NCBIGene:ABCD", "NCBIGene:GENE:1017"]})
    assert response.status_code == 200
    response_json = response.json()
    assert response_json == {"NCBIGene:ABCD": None, "NCBIGene:GENE:1017": None}


def test_get_normalized_nodes_merge():
    host_url = "http://127.0.0.1:8080/get_normalized_nodes"
    response = requests.get(url=host_url, headers=HEADERS, params={"curie": ["MONDO:0005002", "DOID:3812"]})
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 2
    assert "MONDO:0005002" in response_json
    assert "DOID:3812" in response_json


def test_get_normalized_nodes_empty():
    host_url = "http://127.0.0.1:8080/get_normalized_nodes"

    # GET
    response = requests.get(url=host_url, headers=HEADERS, params={"curie": []})
    assert response.status_code == 422
    assert response.reason == "Unprocessable Entity"
    response_json = response.json()
    assert response_json["detail"][0]["msg"] == "ensure this value has at least 1 items"
    assert response_json["detail"][0]["loc"] == ["query", "curie"]

    # POST
    response = requests.post(url=host_url, headers=HEADERS, json={"curies": []})
    assert response.status_code == 422
    assert response.reason == "Unprocessable Entity"
    response_json = response.json()
    assert response_json["detail"][0]["msg"] == "ensure this value has at least 1 items"
    assert response_json["detail"][0]["loc"] == ["body", "curies"]


def x_test_real_result(session):
    host_url = "http://127.0.0.1:8080/query"
    print(f"host_url: {host_url}")

    ac_out_attributes_file = Path(__file__).parent / "resources" / "ac_out_attributes.json"

    with open(ac_out_attributes_file, "r") as pre:
        ac_out_attributes_data = json.load(pre)

    query = reasoner_pydantic.message.Query.parse_obj(ac_out_attributes_data)

    response = requests.post(url=host_url, headers=HEADERS, data=query.json())
    assert response.status_code == 200
    post_merged_from_api = response.json()

    assert len(post_merged_from_api["message"]["results"]) == len(ac_out_attributes_data["message"]["results"])


def test_dupe_edge(session):
    host_url = "http://127.0.0.1:8080/query"
    print(f"host_url: {host_url}")

    pre_merged_dupe_edge_file = Path(__file__).parent / "resources" / "premerged_dupe_edge.json"
    with open(pre_merged_dupe_edge_file, "r") as pre:
        pre_merged_dupe_edge_data = json.load(pre)

    post_merged_dupe_edge_file = Path(__file__).parent / "resources" / "postmerged_dupe_edge.json"
    with open(post_merged_dupe_edge_file, "r") as pre:
        post_merged_dupe_edge_data = json.load(pre)

    query = reasoner_pydantic.message.Query.parse_obj(pre_merged_dupe_edge_data)

    response = requests.post(url=host_url, headers=HEADERS, data=query.json())
    assert response.status_code == 200
    post_merged_from_api = response.json()

    diffs = DeepDiff(post_merged_dupe_edge_data, post_merged_from_api, ignore_order=True)
    assert len(diffs) == 0


def test_input_has_set(session):
    host_url = "http://127.0.0.1:8080/query"
    print(f"host_url: {host_url}")

    input_set_file = Path(__file__).parent / "resources" / "input_set.json"
    with open(input_set_file, "r") as pre:
        input_set_data = json.load(pre)

    query = reasoner_pydantic.message.Query.parse_obj(input_set_data)

    response = requests.post(url=host_url, headers=HEADERS, data=query.json())
    assert response.status_code == 200
    post_merged_from_api = response.json()

    result = post_merged_from_api["message"]["results"][0]
    # There are 2 coming in and no merging, so should be 2 going out
    assert len(result["edge_bindings"]["treats"]) == 2
    assert len(result["node_bindings"]["drug"]) == 2
