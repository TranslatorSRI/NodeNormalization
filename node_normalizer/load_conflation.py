from pathlib import Path
import os
import json
import model.response as nn_model
import redis_adapter
from redis_adapter import RedisConnection
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
@click.option("--conflation-type", "-s", type=click.Choice(nn_model.ConflationType), help="Conflation Type")
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

    try:
        connection_factory: redis_adapter.RedisConnectionFactory = await redis_adapter.RedisConnectionFactory.create_connection_pool(redis_config)

        conflation_db_conn: redis_adapter.RedisConnection = connection_factory.get_connection("conflation_db")

        conflation_pipeline = conflation_db_conn.pipeline()

        line_counter: int = 0
        with open(conflation_file, "r", encoding="utf-8") as cfile:
            logger.info(f"Processing {conflation_file}...")

            # for each line in the file
            for line in cfile:

                # example line:
                # {"id": {"identifier": "NCBIGene:105021066", "label": "tet2"}, "equivalent_identifiers": [{"identifier": "NCBIGene:105021066",
                # "label": "tet2"}, {"identifier": "ENSEMBL:ENSELUG00000017237"}], "type": ["biolink:Gene", "biolink:GeneOrGeneProduct",
                # "biolink:BiologicalEntity", "biolink:NamedThing", "biolink:Entity", "biolink:MacromolecularMachineMixin"]}

                # new format:
                # ["NCBIGene:246497", "UniProtKB:Q8MLQ0"]
                # ["NCBIGene:303135", "UniProtKB:G3V9Z6"]
                # ["NCBIGene:191570", "UniProtKB:G3V782"]
                # ["NCBIGene:101886961", "UniProtKB:A0A0R4IQ08"]

                # load the line into memory
                instance = json.loads(line)

                # We need to include the identifier in the list of identifiers so that we know its position
                key = {"conflation_type": conflation_type.value, "canonical_id": instance[0]}
                equivalent_identifiers = list(instance[1:])

                if equivalent_identifiers:
                    line_counter = line_counter + 1

                    logger.debug(f"key: {key}")

                    value = {"equivalent_identifiers": equivalent_identifiers}
                    # conflation_pipeline.set(identifier, line)
                    logger.debug(f"conflations: {value}")
                    conflation_pipeline.set(str(key), str(value))

                if not dry_run and line_counter % block_size == 0:
                    await RedisConnection.execute_pipeline(conflation_pipeline)

                    # pipelines executed...create a new one
                    conflation_pipeline = conflation_db_conn.pipeline()

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


if __name__ == "__main__":
    main()
