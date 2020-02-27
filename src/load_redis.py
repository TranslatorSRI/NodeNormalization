import redis
import os
import json

# storage for the semantic types and source prefixes
semantic_types: set = set({})
source_prefixes: dict = {}

def get_config():
    cname = os.path.join(os.path.dirname(__file__),'..', 'config.json')
    with open(cname,'r') as json_file:
        data = json.load(json_file)
    return data

def load_redis():
    """Given a compendia directory, load every file there into a running
    redis instance so that it can be read by R3"""
    config = get_config()
    compendia = get_compendia(config)

    for comp in compendia:
        load_compendium(comp,config)

    # get the connection and pipeline to the database
    types_prefixes_redis = get_redis(config, 2)
    types_prefixes_pipeline = types_prefixes_redis.pipeline()

    # at all the semantic types
    for item in semantic_types:
        types_prefixes_pipeline.lpush('semantic_types', item)

    # for each semantic type insert the list of source prefixes
    for item in source_prefixes:
        types_prefixes_pipeline.set(item, json.dumps(source_prefixes[item]))

    # add the data to redis
    types_prefixes_pipeline.execute()

def get_compendia(config):
    """Return the list of compendum files to load"""
    return [os.path.join(config.get('compendium_directory'), file_name) for file_name in os.listdir(config.get('compendium_directory'))]

def get_redis(config,dbid):
    """Return a redis instance"""
    return redis.StrictRedis(host=config['redis_host'],
                             port=int(config['redis_port']),
                             db = dbid,
                             password = config['redis_password'])

def load_compendium(compendium_filename, config):
    """Given the full path to a compendium, load it into redis so that it can
    be read by R3.  We also load extra keys, which are the uppercased 
    identifiers, for ease of use"""

    term2id_redis = get_redis(config,0)
    id2instance_redis = get_redis(config,1)

    term2id_pipeline = term2id_redis.pipeline()
    id2instance_pipeline = id2instance_redis.pipeline()

    with open(compendium_filename,'r') as compendium:
        print(f'Processing {compendium_filename}...')
        for line in compendium:
            instance = json.loads(line)

            # save the identifier
            identifier = instance['id']['identifier']

            # save the semantic type
            semantic_type = instance['type'][0]

            # save the semantic types in a set to avoid duplicates
            semantic_types.update([semantic_type])

            # have we saved this one already
            if source_prefixes.get(semantic_type) is None:
                # add this one in
                source_prefixes[semantic_type] = {}

            # go through each equivalent identifier in the data row
            for equivalent_id in instance['equivalent_identifiers']:
                # split the identifier to just get the data source out of the curie
                source_prefix = equivalent_id['identifier'].split(':')[0]

                # is the source prefix already there? if not save it
                if source_prefixes[semantic_type].get(source_prefix) is None:
                    source_prefixes[semantic_type][source_prefix] = 1
                # else just increment the count for the semantic type/source
                else:
                    source_prefixes[semantic_type][source_prefix] = source_prefixes[instance['type'][0]][source_prefix] + 1

                # equivalent_id might be an array, where the first element is
                # the identifier, or it might just be a string. 
                # Not implemented worrying about that yet.
                equivalent_id = equivalent_id['identifier']
                term2id_pipeline.set(equivalent_id, identifier)
                term2id_pipeline.set(equivalent_id.upper(), identifier)

            id2instance_pipeline.set(identifier, line)
        print(f'Dumping to term2id db ...')
        term2id_pipeline.execute()

        print(f'Dumping to id2instance db ...')
        id2instance_pipeline.execute()

        print(f'Done loading {compendium_filename}...')

if __name__ == '__main__':
    load_redis()