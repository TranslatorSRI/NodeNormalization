import redis
import os
import json
import jsonschema
from itertools import islice
from datetime import datetime


##############
# Class: NodeNormalization
#
# By: Yaphete Kebede
# Date: 1/2020
# Desc: Class that gets all node definitions from a series of flat files
#       and produces Translator compliant nodes which are then loaded into a redis database.
##############
class NodeNormalization:
    # storage for the semantic types and source prefixes
    semantic_types: set = set()
    source_prefixes: dict = {}

    # Storage for the configuration params
    _config: json = None

    def __init__(self):
        self._config = self.get_config()

        self._compendium_directory: str = self._config['compendium_directory']
        self._redis_host: str = self._config['redis_host']
        self._redis_password: str = self._config['redis_password']
        self._redis_port: int = self._config['redis_port']
        self._test_mode: int = self._config['test_mode']

        with open('./src/valid_data_format.json') as json_file:
            self._validate_with = json.load(json_file)

        pass

    @staticmethod
    def get_config() -> json:
        """ class constructor """
        cname = os.path.join(os.path.dirname(__file__), '..', 'config.json')

        with open(cname, 'r') as json_file:
            data = json.load(json_file)

        return data

    def load(self) -> bool:
        """Given a compendia directory, load every file there into a running
        redis instance so that it can be read by R3"""

        if self._test_mode == 1:
            self.print_debug_msg(f'Test mode enabled. No data will be produced.', True)

        # init the return value
        ret_val = True

        try:
            # get the list of files in the directory
            compendia: list = self.get_compendia()

            # for each file validate and process
            for comp in compendia:
                # check the validity of the file
                if self.validate_compendia(comp):
                    # try to load the file
                    if not self.load_compendium(comp):
                        self.print_debug_msg(f'Compendia file {comp} did not load.', True)
                        continue
                else:
                    self.print_debug_msg(f'Compendia file {comp} is invalid.', True)
                    continue

            # get the connection and pipeline to the database
            types_prefixes_redis: redis.Redis = self.get_redis(2)
            types_prefixes_pipeline = types_prefixes_redis.pipeline()

            # create a command to get the current semantic types
            types_prefixes_pipeline.lrange('semantic_types', 0, -1)

            # get the current list of semantic types
            vals = types_prefixes_pipeline.execute()

            # get the values and insure they are strings
            current_types: set = set(x.decode("utf-8") for x in vals[0])

            # remove any dupes
            self.semantic_types = self.semantic_types.difference(current_types)

            if len(self.semantic_types) > 0:
                # add all the semantic types
                types_prefixes_pipeline.lpush('semantic_types', *self.semantic_types)

            # for each semantic type insert the list of source prefixes
            for item in self.source_prefixes:
                types_prefixes_pipeline.set(item, json.dumps(self.source_prefixes[item]))

            if self._test_mode != 1:
                # add the data to redis
                types_prefixes_pipeline.execute()

        except Exception as e:
            self.print_debug_msg(f'Exception thrown in load(): {e}', True)
            ret_val = False

        # return to the caller
        return ret_val

    def validate_compendia(self, in_file):
        # open the file to validate
        with open(in_file, 'r') as compendium:
            self.print_debug_msg(f'Validating {in_file}...', True)

            # sample the file
            for line in islice(compendium, 5):
                try:
                    instance: dict = json.loads(line)

                    # validate the incoming json against the spec
                    jsonschema.validate(instance=instance, schema=self._validate_with)
                # catch any exceptions
                except Exception as e:
                    self.print_debug_msg(f'Exception thrown in validate_compendia({in_file}): {e}', True)
                    return False

        return True

    def get_compendia(self):
        """Return the list of compendum files to load"""
        return [os.path.join(self._compendium_directory, file_name) for file_name in os.listdir(self._compendium_directory)]

    def get_redis(self, dbid):
        """Return a redis instance"""
        return redis.StrictRedis(host=self._redis_host, port=self._redis_port, db=dbid, password=self._redis_password)

    def load_compendium(self, compendium_filename: str) -> bool:
        """Given the full path to a compendium, load it into redis so that it can
        be read by R3.  We also load extra keys, which are the upper-cased
        identifiers, for ease of use"""

        try:
            term2id_redis = self.get_redis(0)
            id2instance_redis = self.get_redis(1)

            term2id_pipeline = term2id_redis.pipeline()
            id2instance_pipeline = id2instance_redis.pipeline()

            with open(compendium_filename, 'r', encoding="utf-8") as compendium:
                self.print_debug_msg(f'Processing {compendium_filename}...', True)

                # init a line counter
                line_counter: int = 0

                # for each line in the file
                for line in compendium:
                    line_counter = line_counter + 1

                    # load the line into memory
                    instance: dict = json.loads(line)

                    # save the identifier
                    identifier: str = instance['id']['identifier']

                    # for each semantic type in the list
                    for semantic_type in instance['type']:
                        # save the semantic type in a set to avoid duplicates
                        self.semantic_types.add(semantic_type)

                        #  create a source prefix if it has not been encountered
                        if self.source_prefixes.get(semantic_type) is None:
                            self.source_prefixes[semantic_type] = {}

                        # go through each equivalent identifier in the data row
                        # each will be assigned the semantic type information
                        for equivalent_id in instance['equivalent_identifiers']:
                            # split the identifier to just get the data source out of the curie
                            source_prefix: str = equivalent_id['identifier'].split(':')[0]

                            # save the source prefix if no already there
                            if self.source_prefixes[semantic_type].get(source_prefix) is None:
                                self.source_prefixes[semantic_type][source_prefix] = 1
                            # else just increment the count for the semantic type/source
                            else:
                                self.source_prefixes[semantic_type][source_prefix] += 1

                            # equivalent_id might be an array, where the first element is
                            # the identifier, or it might just be a string. not worrying about that case yet.
                            equivalent_id = equivalent_id['identifier']
                            term2id_pipeline.set(equivalent_id, identifier)
                            term2id_pipeline.set(equivalent_id.upper(), identifier)

                        id2instance_pipeline.set(identifier, line)

                if self._test_mode != 1:
                    print(f'Dumping to term2id db ...')
                    term2id_pipeline.execute()

                    print(f'Dumping to id2instance db ...')
                    id2instance_pipeline.execute()

                print(f'Done loading {compendium_filename}...')
        except Exception as e:
            self.print_debug_msg(f'Exception thrown in load_compendium({compendium_filename}), line {line_counter}: {e}', True)
            return False

        # return to the caller
        return True

    def print_debug_msg(self, msg: str, force: bool = False):
        """ Prints a debug message if enabled in the config file """
        if self._config['debug_messages'] == 1 or force:
            now: datetime = datetime.now()

            print(f'{now.strftime("%Y/%m/%d %H:%M:%S")} - {msg}')
