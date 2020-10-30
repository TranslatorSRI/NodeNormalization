from node_normalizer.loader import NodeLoader
import os
import pytest


def test_nn_load():
    node_loader: NodeLoader = NodeLoader(True)

    this_dir = os.path.dirname(os.path.realpath(__file__))

    node_loader._test_mode = 1

    assert(node_loader.load_compendium(os.path.join(this_dir, "datafile.json"), 5))


def test_nn_record_validation():
    node_loader: NodeLoader = NodeLoader(True)

    this_dir = os.path.dirname(os.path.realpath(__file__))

    ret_val = node_loader.validate_compendia(os.path.join(this_dir, "datafile.json"))

    assert ret_val

    ret_val = node_loader.validate_compendia(os.path.join(this_dir, "datafile_with_errors.json"))

    assert(not ret_val)
