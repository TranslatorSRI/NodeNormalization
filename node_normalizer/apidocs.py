"""API documentation"""
from jinja2 import Environment, FileSystemLoader
from sanic import Blueprint, response
from swagger_ui_bundle import swagger_ui_3_path

import node_normalizer.versioner as vers

vers.version_spec('1.0.1')

# build Swagger UI
env = Environment(
    loader=FileSystemLoader(swagger_ui_3_path)
)

template = env.get_template('index.j2')
html_content = template.render(
    title="Redis-REST with Referencing",
    openapi_spec_url="./openapi.yml",
)
with open('swagger_ui/index.html', 'w') as f:
    f.write(html_content)

# serve apidocs
bp = Blueprint('apidocs', url_prefix='/apidocs', strict_slashes=True)
bp.static('/', 'swagger_ui/index.html')
bp.static('/', swagger_ui_3_path)
bp.static('/openapi.yml', 'swagger_ui/openapi.yml')


@bp.route('')
def redirect(request):
    """Redirect to url with trailing slash."""
    return response.redirect('/apidocs/')

app_info = {
    'title': 'Node Normalization',
    'version': '1.0.1',
    'description': '''
Node normalization takes a CURIE, and returns: <ol> <li>The preferred 
CURIE for this entity <li>All other known equivalent identifiers for the entity 
<li>Semantic types for the entity as defined by the <a href="https://biolink.github.io/biolink-model/">BioLink 
Model</a> </ol> The data served by Node Normalization is created by 
<a href="https://github.com/TranslatorIIPrototypes/Babel">Babel</a>, 
which attempts to find identifier equivalences, and makes sure that CURIE prefixes 
are BioLink Model Compliant.  To determine whether Node Normalization is likely 
to be useful, check /get_semantic_types, which lists the BioLink semantic types 
for which normalization has been attempted, and /get_curie_prefixes, which lists 
the number of times each prefix is used for a semantic type.
''',
    'contact': {
        'email': 'kebedey@renci.org'
    },
    'license': {
        'name': 'MIT',
        'url': 'https://opensource.org/licenses/MIT'
    },
    'termsOfService': 'http://robokop.renci.org:7055/tos?service_long=Redis-REST+with+Referencing&provider_long=the+Translator+Consortium'
}
