from src.NodeNormalization import NodeNormalization
import pytest


def test_nn_load():
    nn: NodeNormalization = NodeNormalization()

    nn._test_mode = 1

    assert(nn.load_compendium("./tests/datafile.json"), 5)

def test_nn_record_validation():
    nn: NodeNormalization = NodeNormalization()

    assert(nn.validate_compendia("./tests/datafile.json"))

    ret_val = nn.validate_compendia("./tests/datafile_with_errors.json")

    assert(ret_val == False)
