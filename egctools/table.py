import re
import importlib.resources
from jinja2 import Environment, FileSystemLoader
_data = importlib.resources.files("egctools").joinpath("data")

# from https://stackoverflow.com/questions/16259923/
#       how-can-i-escape-latex-special-characters-inside-django-templates
def _tex_escape(text):
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless{}',
        '>': r'\textgreater{}',
    }
    regex = re.compile('|'.join(re.escape(str(key)) for
      key in sorted(conv.keys(), key = lambda item: - len(item))))
    return regex.sub(lambda match: conv[match.group()], text)

def create(s, fmt, name, **params):
  env = Environment(loader=FileSystemLoader(str(_data)))
  env.filters["texesc"] = _tex_escape
  template_filename = f"{fmt}_table_{name}.j2"
  template = env.get_template(template_filename)
  render_params = s.copy()
  render_params.update(params)
  return template.render(render_params)
