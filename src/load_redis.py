import redis
import os
import json

def get_config():
    cname = os.path.join(os.path.dirname(__file__),'..', 'config.json')
    with open(cname,'r') as json_file:
        data = load(json_file)
    return data

def load_redis():
    """Given a compendia directory, load every file there into a running
    redis instance so that it can be read by R3"""
    config = get_config()
    compendia = get_compendia(config)
    for comp in compendia:
        load_compendium(comp,config)

def get_compendia(config):
    """Return the list of compendum files to load"""
    return []

def get_redis(config,dbid):
    """Return a redis instance"""
    return redis.StrictRedis(host=config['redis_host'], 
                             port=int(config['redis_port']),
                             db = dbid,
                             password = config['redis_password'])

def load_compendum(compendium_filename,config):
    """Given the full path to a compendium, load it into redis so that it can
    be read by R3.  We also load extra keys, which are the uppercased 
    identifiers, for ease of use"""
    term2id_redis = get_redis(config,0)
    id2instance_redis = get_redis(config,1)
    term2id_pipeline = term2id_redis.pipeline()
    id2instance_pipeline = id2instance_redis.pipeline()
    with open(compendium_filename,'r') as compendium:
        for line in compendium:
            instance = json.reads(line)
            identifier = instance['id']
            for equivalent_id in instance['equivalent_identifiers']:
                #equivalent_id might be an array, where the first element is 
                # the identifier, or it might just be a string. 
                #Not implemented worrying about that yet.
                term2id_pipeline.set(equivalent_id,identifier)
                term2id_pipeline.set(equivalent_id.upper(),identifier)
            id2instance_pipeline.set(identifier, line)
