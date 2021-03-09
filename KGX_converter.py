import os
from node_normalizer.loader import NodeLoader


def convert_to_kgx():
    # instantiate the class that does all the work
    loader = NodeLoader()

    # call to load redis instances with normalized node data
    success: bool = loader.convert_to_kgx('KGX_NN_data')

    # check the return
    if not success:
        loader.print_debug_msg(f'Failed to convert compendia data.', True)
    else:
        loader.print_debug_msg(f'Success', True)


if __name__ == '__main__':
    convert_to_kgx()
