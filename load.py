from src.NodeNormalization import NodeNormalization


if __name__ == '__main__':
    # instantiate the class that does all the work
    nn = NodeNormalization()

    # call to load redis instances with normalized node data
    success: bool = nn.load()

    # check the return
    if not success:
        nn.print_debug_msg(f'Failed to load node normalization data.', True)
    else:
        nn.print_debug_msg(f'Success', True)
