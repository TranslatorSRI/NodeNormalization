from pathlib import Path

import pytest

from node_normalizer.loader import NodeLoader


good_json = Path(__file__).parent / 'resources' / 'datafile.json'
bad_json = Path(__file__).parent / 'resources' / 'datafile_with_errors.json'


def test_nn_load():
    node_loader: NodeLoader = NodeLoader()

    node_loader._test_mode = 1

    assert(node_loader.load_compendium(good_json, 5))


def test_nn_record_validation():
    node_loader: NodeLoader = NodeLoader()

    ret_val = node_loader.validate_compendia(good_json)

    assert ret_val

    ret_val = node_loader.validate_compendia(bad_json)

    assert(not ret_val)
