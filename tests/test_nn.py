from src.NodeNormalizer import NodeNormalization
import os
import pytest

def test_nn_load():
    nn: NodeNormalization = NodeNormalization(True)

    this_dir = os.path.dirname(os.path.realpath(__file__))

    nn._test_mode = 1

    assert(nn.load_compendium(os.path.join(this_dir, "datafile.json"), 5))

def test_nn_record_validation():
    nn: NodeNormalization = NodeNormalization(True)

    this_dir = os.path.dirname(os.path.realpath(__file__))

    ret_val = nn.validate_compendia(os.path.join(this_dir, "datafile.json"))

    assert ret_val

    ret_val = nn.validate_compendia(os.path.join(this_dir, "datafile_with_errors.json"))

    assert(not ret_val)
