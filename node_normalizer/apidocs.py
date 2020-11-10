"""API documentation"""
from pathlib import Path
from typing import Dict

from yaml import load, SafeLoader


with open(Path(__file__).parent / 'resources' / 'openapi.yml', 'r') as apd_file:
    api_docs = load(apd_file, Loader=SafeLoader)


def get_app_info() -> Dict[str, str]:
    return {
        k : v for k,v in api_docs['info'].items() if k in [
            'title',
            'version',
            'description',
            'contact',
            'license',
            'termsOfService',
        ]
    }

# TODO use examples from openapi.yml to drive examples
