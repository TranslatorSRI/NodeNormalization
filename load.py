from node_normalizer.loader import NodeLoader
import asyncio
import sys


async def load_redis():
    # instantiate the class that does all the work
    loader = NodeLoader()

    # call to load redis instances with normalized node data
    success: bool = await loader.load(100_000)

    # check the return
    if not success:
        print('Failed to load node normalization data.')
    else:
        print('Success')
    return success


if __name__ == '__main__':
    sys.exit(asyncio.run(load_redis()))
