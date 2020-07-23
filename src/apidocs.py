"""API documentation for Redis-REST with referencing."""
from jinja2 import Environment, FileSystemLoader
from sanic import Blueprint, response
from swagger_ui_bundle import swagger_ui_3_path

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
