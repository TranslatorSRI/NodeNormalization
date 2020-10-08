from src.NodeNormalizer import NodeNormalizer


def load_redis():
    # instantiate the class that does all the work
    normalizer = NodeNormalizer()

    # call to load redis instances with normalized node data
    success: bool = normalizer.load(500000)

    # check the return
    if not success:
        normalizer.print_debug_msg(f'Failed to load node normalization data.', True)
    else:
        normalizer.print_debug_msg(f'Success', True)


if __name__ == '__main__':
    load_redis()
