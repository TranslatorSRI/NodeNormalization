import asyncio
import hashlib
import os
from pathlib import Path
from itertools import combinations
import json

import click
from node_normalizer.util import validate_compendium, LoggingUtil

logger = LoggingUtil.init_logging()


@click.command(no_args_is_help=True)
@click.option("--compendium-file", "-c", help="Compendia File", multiple=True)
@click.option("--output-directory", "-o", help="Output Directory")
@click.option("--output-file-prefix", "-p", help="Output File Prefix")
@click.option("--dry-run", "-d", help="Dry Run", default=False)
@click.option("--redis-config", "-r", help="Redis Config File", type=click.Path(), default=Path(__file__).parent.parent / "redis_config.yaml")
def convert_to_kgx(compendium_file, output_directory, output_file_prefix, dry_run, redis_config) -> bool:
    """
    Given a compendia directory, create a KGX node file
    """

    # init the return value
    ret_val = True

    line_counter: int = 0

    try:

        nodes: list = []
        edges: list = []
        pass_nodes: list = []

        for comp in compendium_file:
            if not validate_compendium(comp, logger):
                logger.warning(f"Compendia file {comp} is invalid.")
                return False

        # open the output file and start loading it
        with open(os.path.join(output_directory, output_file_prefix + "_nodes.jsonl"), "w", encoding="utf-8") as node_file, open(
            os.path.join(output_directory, output_file_prefix + "_edges.jsonl"), "w", encoding="utf-8"
        ) as edge_file:

            # set the flag for suppressing the first ",\n" in the written data
            first = True

            # for each file validate and process
            for comp in compendium_file:

                with open(comp, "r", encoding="utf-8") as compendium:
                    logger.info(f"Processing {comp}...")

                    # get the name of the source
                    # source = os.path.split(comp)[-1]

                    # for each line in the file
                    for line in compendium:
                        # increment the record counter
                        line_counter += 1

                        # clear storage for this pass
                        pass_nodes.clear()

                        # load the line into memory
                        instance: dict = json.loads(line)

                        # all ids (even the root one) are in the equivalent identifiers
                        if len(instance["identifiers"]) > 0:
                            # loop through each identifier and create a node
                            for equiv_id in instance["identifiers"]:
                                # check to see if there is a label. if there is use it
                                if "l" in equiv_id:
                                    name = equiv_id["l"]
                                else:
                                    name = ""

                                # add the node to the ones in this pass
                                pass_nodes.append(
                                    {
                                        "id": equiv_id["i"],
                                        "name": name,
                                        "category": instance["type"],
                                        "equivalent_identifiers": list(x["i"] for x in instance["identifiers"]),
                                    }
                                )

                            # get the combinations of the nodes in this pass
                            combos = combinations(pass_nodes, 2)

                            # for all the node combinations create an edge between them
                            for c in combos:
                                # create a unique id
                                record_id: str = c[0]["id"] + c[1]["id"] + f"{comp}"

                                # save the edge
                                edges.append(
                                    {
                                        "id": f'{hashlib.md5(record_id.encode("utf-8")).hexdigest()}',
                                        "subject": c[0]["id"],
                                        "predicate": "biolink:same_as",
                                        "object": c[1]["id"],
                                    }
                                )

                        # save the nodes in this pass to the big list
                        nodes.extend(pass_nodes)

                        # did we reach the write threshold
                        if line_counter == 10000:
                            # first time in doesnt get a leading comma
                            # if first:
                            #     prefix = ""
                            # else:
                            #     prefix = "\n"

                            # reset the first record flag
                            first = False

                            # reset the line counter for the next group
                            line_counter = 0

                            # get all the nodes in a string and write them out
                            nodes_to_write = "\n".join([json.dumps(node) for node in nodes])
                            node_file.write(nodes_to_write + "\n")

                            # are there any edges to output
                            if len(edges) > 0:
                                # get all the edges in a string and write them out
                                edges_to_write = "\n".join([json.dumps(edge) for edge in edges])
                                edge_file.write(edges_to_write + "\n")

                            # reset for the next group
                            nodes.clear()
                            edges.clear()

                    # pick up any remainders in the file
                    if len(nodes) > 0:
                        nodes_to_write = "\n".join([json.dumps(node) for node in nodes])
                        node_file.write(nodes_to_write + "\n")

                    if len(edges) > 0:
                        edges_to_write = "\n".join([json.dumps(edge) for edge in edges])
                        edge_file.write(edges_to_write + "\n")

    except Exception as e:
        logger.error(f"Exception thrown in convert_to_KGX(): {e}")
        ret_val = False

    # return to the caller
    return ret_val


if __name__ == "__main__":
    convert_to_kgx()
