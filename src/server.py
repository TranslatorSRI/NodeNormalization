"""Sanic server for Redis-REST with referencing."""
import json
import os

import aioredis
from sanic import Sanic, response

from src.apidocs import bp as apidocs_blueprint

app = Sanic()
app.config.ACCESS_LOG = False
app.blueprint(apidocs_blueprint)

redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', 6379)


async def startup_connections(app, loop):
    """Start up Redis connection."""
    app.redis_connection0 = await aioredis.create_redis_pool(
        f'redis://{redis_host}:{redis_port}', db=0)
    app.redis_connection1 = await aioredis.create_redis_pool(
        f'redis://{redis_host}:{redis_port}', db=1)
    app.redis_connection2 = await aioredis.create_redis_pool(
        f'redis://{redis_host}:{redis_port}', db=2)


async def shutdown_connections(app, loop):
    """Shut down Redis connection."""
    app.redis_connection0.close()
    await app.redis_connection0.wait_closed()
    app.redis_connection1.close()
    await app.redis_connection2.wait_closed()
    app.redis_connection2.close()
    await app.redis_connection2.wait_closed()


@app.route('/get_normalized_nodes')
async def get_normalized_node_handler(request):
    """Get value(s) for key(s).

    Use GET for single key, MGET for multiple.
    """
    # was an arg passed in
    if len(request.args) != 0:
        if isinstance(request.args['curie'], list):
            references = await app.redis_connection0.mget(*request.args['curie'], encoding='utf-8')
            references_nonnan = [reference for reference in references if reference is not None]
            if not references_nonnan:
                return response.text('No matches found for the specified curie(s).', status=404)
            values = await app.redis_connection1.mget(*references_nonnan, encoding='utf-8')
            values = [json.loads(value) if value is not None else None for value in values]
            dereference = dict(zip(references_nonnan, values))
            return response.json({
                key: dereference[reference] if reference is not None else None
                for key, reference in zip(request.args['curie'], references)
            })
        else:
            reference = await app.redis_connection0.get(request.args['curie'], encoding='utf-8')
            if reference is None:
                return response.json({request.args['curie']: None})
            value = await app.redis_connection1.get(reference, encoding='utf-8')
            value = json.loads(value) if value is not None else None
            return response.json({request.args['curie']: value})
    else:
        return response.text('Error parsing query string.', status=500)

@app.route('/get_semantic_types')
async def get_semantic_types_handler(request):
    # look for all biolink semantic types
    types = await app.redis_connection2.lrange('semantic_types', 0 ,-1, encoding='utf-8')

    # did we get any data
    if not types:
        return response.text('No semantic types discovered.', status=404)

    # get the distinct list of Biolink model types in the correct format
    ret_val = {'semantic_types': {'types': types}}

    # return the data to the caller
    return response.json(ret_val)

@app.route('/get_curie_prefixes')
async def get_curie_prefixes_handler(request):
    # storage for the returned data
    ret_val: dict = {}

    # was an arg passed in
    if len(request.args) != 0:
        try:
            # is the input a list
            if isinstance(request.args['semantic_type'], list):
                for item in request.args['semantic_type']:
                    # get the curies for this type
                    curies = await app.redis_connection2.get(item, encoding='utf-8')

                    # did we get any data
                    if not curies:
                        curies = '{' + f'"{item}"' + ': "Not Found"}'

                    curies = json.loads(curies)

                    # set the return data
                    ret_val[item] = {'curie_prefix': [curies]}
            # else it must be a singleton+6+9++
            else:
                # get the curies for this type
                curies = await app.redis_connection2.get(request.args["semantic_type"], encoding='utf-8')

                # did we get any data
                if not curies:
                    return response.text(f'No curie discovered for {request.args["semantic_type"]}.', status=404)

                # set the return data
                ret_val[request.args['semantic_type']] = {'curie_prefix': [curies]}
        except Exception:
            return response.text('Error parsing query string.', status=500)
    else:
        types = await app.redis_connection2.lrange('semantic_types', 0, -1, encoding='utf-8')

        for item in types:
            # get the curies for this type
            curies = await app.redis_connection2.get(item, encoding='utf-8')

            # did we get any data
            if not curies:
                curies = '{' + f'"{item}"' + ': "Not Found"}'

            curies = json.loads(curies)

            # set the return data
            ret_val[item] = {'curie_prefix': [curies]}

# return the data to the caller
    return response.json(ret_val)

app.register_listener(startup_connections, 'after_server_start')
app.register_listener(shutdown_connections, 'before_server_stop')
