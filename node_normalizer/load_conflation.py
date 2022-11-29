from pathlib import Path
import os
from itertools import islice
import json
import jsonschema
from model.response import ConflationType
import redis_adapter
from redis_adapter import RedisConnectionFactory, RedisConnection
import asyncclick as click
import logging
from logging.config import dictConfig

dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {"default": {"format": "%(asctime)s | %(levelname)s | %(module)s:%(funcName)s | %(message)s"}},
        "handlers": {
            "console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "default"},
        },
        "loggers": {
            "node-norm": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "ERROR")},
        },
    }
)
logger = logging.getLogger("node-norm")
logger.propagate = False


@click.command(no_args_is_help=True)
@click.option("--conflation-file", "-c", help="Conflation File", type=click.Path())
@click.option("--conflation-type", "-s", type=click.Choice(ConflationType), help="Conflation Type")
# @click.option("--conflation-db", "-s", help="Redis DB for conflation data")
@click.option("--block-size", "-b", help="Block Size", default=1000)
@click.option("--dry-run", "-d", help="Dry Run", default=False, is_flag=True)
@click.option("--redis-config", "-r", help="Redis Config File", type=click.Path(), default=Path(__file__).parent.parent / "redis_config.yaml")
async def main(conflation_file, conflation_type, block_size, dry_run, redis_config):
    """
    Given a conflation, load it into a redis so that it can
    be read by R3.
    """

    # check the validity
    if not os.path.exists(conflation_file):
        logger.warning(f"Conflation file {conflation_file} is invalid.")
        return False

    # check the validity
    if not validate(conflation_file):
        logger.warning(f"Conflation file {conflation_file} is invalid.")
        return False

    try:
        connection_factory: redis_adapter.RedisConnectionFactory = await redis_adapter.RedisConnectionFactory.create_connection_pool(redis_config)

        conflation_db_conn: redis_adapter.RedisConnection = connection_factory.get_connection("conflation_db")
        conflation_type_db_conn: redis_adapter.RedisConnection = connection_factory.get_connection("conflation_type_db")

        conflation_pipeline = conflation_db_conn.pipeline()
        conflation_type_pipeline = conflation_type_db_conn.pipeline()

        line_counter: int = 0
        with open(conflation_file, "r", encoding="utf-8") as cfile:
            logger.info(f"Processing {conflation_file}...")

            # for each line in the file
            for line in cfile:

                # example line:
                # {"id": {"identifier": "NCBIGene:105021066", "label": "tet2"}, "equivalent_identifiers": [{"identifier": "NCBIGene:105021066",
                # "label": "tet2"}, {"identifier": "ENSEMBL:ENSELUG00000017237"}], "type": ["biolink:Gene", "biolink:GeneOrGeneProduct",
                # "biolink:BiologicalEntity", "biolink:NamedThing", "biolink:Entity", "biolink:MacromolecularMachineMixin"]}

                # load the line into memory
                instance: dict = json.loads(line)

                # We need to include the identifier in the list of identifiers so that we know its position
                key = {"conflation_type": conflation_type.value, "canonical_id": instance["id"]}
                equivalent_identifiers = list(instance["equivalent_identifiers"])

                if equivalent_identifiers[0] == instance["id"]:
                    del equivalent_identifiers[0]

                if equivalent_identifiers:
                    line_counter = line_counter + 1

                    logger.debug(f"key: {key}")

                    value = {"equivalent_identifiers": equivalent_identifiers}
                    # conflation_pipeline.set(identifier, line)
                    logger.debug(f"conflations: {value}")
                    conflation_pipeline.set(key, value)

                    semantic_types = instance["type"]
                    logger.debug(f"types: {semantic_types}")
                    conflation_type_pipeline.set(key, semantic_types)

                if not dry_run and line_counter % block_size == 0:
                    await RedisConnection.execute_pipeline(conflation_pipeline)
                    await RedisConnection.execute_pipeline(conflation_type_pipeline)

                    # pipelines executed...create a new one
                    conflation_pipeline = conflation_db_conn.pipeline()
                    conflation_type_pipeline = conflation_type_db_conn.pipeline()

                    logger.info(f"{line_counter} {conflation_file} lines processed")

                # break
            if not dry_run:
                await RedisConnection.execute_pipeline(conflation_pipeline)
                logger.info(f"{line_counter} {conflation_file} total lines processed")

            logger.info(f"Done loading {conflation_file}...")
    except Exception as e:
        logger.error(f"Exception thrown in load_conflation({conflation_file}), line {line_counter}: {e}")
        return False

    # return to the caller
    return True


def validate(in_file):
    # open the file to validate
    # used https://extendsclass.com/json-schema-validator.html to produce the schema
    json_schema = Path(__file__).parent / "resources" / "valid_conflation_data_format.json"
    with open(in_file, "r") as conflation, open(json_schema, "r", encoding="UTF-8") as json_file:
        logger.info(f"Validating {in_file}...")
        validation_schema = json.load(json_file)
        # sample the file
        for line in islice(conflation, 5):
            try:
                instance: dict = json.loads(line)
                # validate the incoming json against the spec
                jsonschema.validate(instance=instance, schema=validation_schema)
            # catch any exceptions
            except Exception as e:
                logger.error(f"Exception thrown in validate: ({in_file}): {e}")
                return False

    return True


if __name__ == "__main__":
    main()
