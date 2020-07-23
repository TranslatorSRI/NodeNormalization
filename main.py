#!/usr/bin/env python

"""Run Redis-REST with referencing."""
import argparse
from src.server import app

parser = argparse.ArgumentParser(description='Start REST interface for Redis.')
parser.add_argument('--host', default='0.0.0.0', type=str)
parser.add_argument('--port', default=6380, type=int)

args = parser.parse_args()

app.run(
    host=args.host,
    port=args.port,
    debug=False,
)
