import asyncio
import json
import logging
from pathlib import Path

import nn_io_rs
from sssom.parsers import parse_sssom_table

from node_normalizer.loader import NodeLoader

logger = logging.getLogger()

good_sssom = Path(__file__).parent / "resources" / "Cell.sssom.tsv"
good_cell_json = Path(__file__).parent / "resources" / "Cell.json"


good_json = Path(__file__).parent / "resources" / "datafile.json"
bad_json = Path(__file__).parent / "resources" / "datafile_with_errors.json"


def test_nn_load():
    node_loader: NodeLoader = NodeLoader()
    node_loader._test_mode = 1
    assert asyncio.run(node_loader.load_compendium(str(good_json), 5))


def test_nn_cell_load():
    node_loader: NodeLoader = NodeLoader()
    # node_loader._test_mode = 1
    assert asyncio.run(node_loader.load_compendium(str(good_cell_json), 5))


def test_nn_load_with_sssom():
    node_loader: NodeLoader = NodeLoader()
    # node_loader._test_mode = 1
    ret = asyncio.run(node_loader.load_compendium(str(good_sssom), 5))
    # ret = asyncio.run(node_loader.load_compendium_sssom(str(good_sssom), 5))
    assert ret


def test_deserialize_sssom():
    mapping_set_data_frame = parse_sssom_table(file_path=good_sssom)
    group = mapping_set_data_frame.df.groupby(["subject_category", "subject_id", "subject_label"])

    for (subject_category, subject_id, subject_label), entries in group:
        logger.info(f"subject_category: {subject_category}, subject_id: {subject_id}, subject_label: {subject_label}")

        ic_values = set()
        for other in entries.loc[:, "other"]:
            if other is not None:
                other_json = json.loads(other)
                if "subject_information_content" in other_json:
                    ic_values.add(other_json["subject_information_content"])

        logger.info(f"ic_values: {ic_values}")

        if len(ic_values) > 0:
            logger.warning(f"len(ic_values) is > 0 across entries")

        ic_value = next(iter(ic_values))

        for (object_id, object_label, other) in entries[["object_id", "object_label", "other"]].values:
            if subject_id == object_id and subject_label == object_label:
                continue

            logger.info(f"object_id: {object_id}, object_label: {object_label}, other: {other}")

    assert True


def test_nn_sssom_converter():
    entries = nn_io_rs.sssom_to_legacy_format(str(good_sssom))
    assert type(entries) == list and len(entries) > 8000 and json.loads(entries[0])["type"] == "biolink:Cell"


def test_nn_record_validation():
    node_loader: NodeLoader = NodeLoader()
    ret_val = node_loader.validate_compendia(good_json)
    assert ret_val

    ret_val = node_loader.validate_compendia(bad_json)
    assert not ret_val

    ret_val = node_loader.validate_compendia_sssom(good_sssom)
    assert ret_val

