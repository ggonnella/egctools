import textformats
from collections import defaultdict
import re
import importlib.resources
_data = importlib.resources.files("egctools").joinpath("data")
_egcspec = _data.joinpath("egc-spec")
_specfile = _egcspec.joinpath("egc.tf.yaml")
SPEC = textformats.Specification(str(_specfile))

def parsed_line(s):
  elements = SPEC["line"].decode(s.rstrip("\n"))
  return elements

def parsed_lines(fname):
  for line in open(fname):
    yield parsed_line(line)

def unparsed_and_parsed_lines(fname):
  for line in open(fname):
    yield (line.rstrip("\n"), parsed_line(line))

def collect_lines_with_id(fname):
  lines = defaultdict(dict)
  for line in parsed_lines(fname):
    if 'id' in line:
      rt = line['record_type']
      lines[rt][line['id']] = line
  return lines

def lines_index(fname):
  lines = []
  lines_idx = defaultdict(\
                lambda: defaultdict(\
                  lambda: {'line': None,
                           'from': defaultdict(list),
                           'to': defaultdict(list)}))
  i = 0
  for uline, line in unparsed_and_parsed_lines(fname):
    lines.append(uline)
    rt = line['record_type']
    document_id_dt = SPEC["external_resource::external_resource_link"]
    if 'id' in line:
      line_id = line['id']
      lines_idx[rt][line_id]['line'] = i
    if 'document_id' in line:
      document_id = document_id_dt.encode(line['document_id'])
    if rt == 'D':
      lines_idx["D"][document_id]['line'] = i
    elif rt == 'S' or rt == 'T':
      lines_idx[rt][line_id]['to']['D'].append(document_id)
      lines_idx["D"][document_id]['from'][rt].append(line_id)
    elif rt == 'G':
      if line['type'] == 'combined' or line['type'] == 'inverted':
        parent_groups = re.findall(r"[a-zA-Z0-9_]+", line["definition"])
        for parent_group_id in parent_groups:
          lines_idx["G"][line_id]['to']['G'].append(parent_group_id)
          lines_idx["G"][parent_group_id]['from']["G"].append(line_id)
      m = re.match(r'^derived:([a-zA-Z0-9_]):.*', line['definition'])
      if m:
        parent_group_id = m.group(1)
        lines_idx["G"][line_id]['to']['G'].append(parent_group_id)
        lines_idx["G"][parent_group_id]['from']["G"].append(line_id)
    elif rt == 'U':
      if line['type'].startswith('homolog_'):
        m = re.match(r'^homolog:([a-zA-Z0-9_])', line['definition'])
        if m:
          parent_unit_id = m.group(1)
          lines_idx["U"][line_id]['to']['U'].append(parent_unit_id)
          lines_idx["U"][parent_unit_id]['from']["U"].append(line_id)
      elif line['type'] == 'set!:arrangement':
        parts = line['definition'].split(',')
        for part in parts:
          m = re.match(r'^([a-zA-Z0-9_]+)$', part)
          if m:
            parent_unit_id = m.group(1)
            lines_idx["U"][line_id]['to']['U'].append(parent_unit_id)
            lines_idx["U"][parent_unit_id]['from']["U"].append(line_id)
      elif line['type'].startswith('*') or line['type'].startswith('set!:'):
        parent_groups = re.findall(r"[a-zA-Z0-9_]+", line["definition"])
        for parent_group_id in parent_groups:
          lines_idx["U"][line_id]['to']['G'].append(parent_group_id)
          lines_idx["G"][parent_group_id]['from']["U"].append(line_id)
    elif rt == 'A' or rt == 'M':
      unit_id = line['unit_id']
      lines_idx[rt][line_id]['to']['U'].append(unit_id)
      if rt == 'A':
        lines_idx["U"][unit_id]['from']['A'].append(line_id)
        if isinstance(line['mode'], dict) and 'reference' in line['mode']:
          ref_id = line['mode']['reference']
          lines_idx["U"][unit_id]['from']['A'].append(ref_id)
          lines_idx["A"][line_id]['to']['U'].append(ref_id)
      else:
        lines_idx["U"][unit_id]['from']['M'].append(i)
    elif rt == 'V' or rt == 'C':
      if isinstance(line['attribute'], dict):
        attributes = [line['attribute']['id1'], line['attribute']['id2']]
      else:
        attributes = [line['attribute']]
      for attribute_id in attributes:
        lines_idx[rt][line_id]['to']['A'].append(attribute_id)
        lines_idx["A"][attribute_id]['from'][rt].append(line_id)
      if rt == 'V':
        groups = [line['group']['id']]
      else:
        groups = [line['group1']['id'], line['group2']['id']]
      for group_id in groups:
        lines_idx[rt][line_id]['to']['G'].append(group_id)
        lines_idx["G"][group_id]['from'][rt].append(line_id)
      if isinstance(line['source'], list):
        sources = line['source']
      else:
        sources = [line['source']]
      for source_id in sources:
        lines_idx[rt][line_id]['to']['S'].append(source_id)
        lines_idx["S"][source_id]['from'][rt].append(line_id)
    i += 1
  return lines, lines_idx

def _extract_S(snippet_id, fname, lines, lines_idx, indent, show_D):
  uline = lines[lines_idx['S'][snippet_id]['line']]
  line = parsed_line(lines[lines_idx['S'][snippet_id]['line']])
  document_id_dt = SPEC["external_resource::external_resource_link"]
  document_id = document_id_dt.encode(line['document_id'])
  results = [indent+uline]
  indent0 = indent+"  "
  indent1 = indent0+"  "
  if show_D:
    results.append(indent0 + lines[lines_idx['D'][document_id]['line']])
  for rt in ['V', 'C']:
    for line_id in lines_idx['S'][snippet_id]['from'][rt]:
      results.append(indent0+lines[lines_idx[rt][line_id]['line']])
      stack = [(ln, indent1) for ln in lines_idx[rt][line_id]['to']['G']]
      while len(stack) > 0:
        group2_id, indent2 = stack.pop()
        results.append(indent2 + lines[lines_idx['G'][group2_id]['line']])
        stack.extend([(ln, indent2+"  ") \
            for ln in lines_idx['G'][group2_id]['to']['G']])
      # get the a lines:
      for attr_id in lines_idx[rt][line_id]['to']['A']:
        results.append(indent1 + lines[lines_idx['A'][attr_id]['line']])
        # get the U lines from A:
        indent2 = indent1 + "  "
        for unit_id in lines_idx['A'][attr_id]['to']['U']:
          results.append(indent2 + lines[lines_idx['U'][unit_id]['line']])
          for model_lineno in lines_idx['U'][unit_id]['to']['M']:
            results.append(indent2 + "  " + lines[model_lineno])
          stack = [(ln, indent2) for ln in lines_idx['U'][unit_id]['to']['U']]
          while len(stack) > 0:
            unit2_id, indent3 = stack.pop()
            results.append(indent3 + lines[lines_idx['U'][unit2_id]['line']])
            stack.extend([(ln, indent3 + "  ") \
                for ln in lines_idx['U'][unit2_id]['to']['U']])
            for model_lineno in lines_idx['U'][unit2_id]['to']['M']:
              results.append(indent3 + "  " + lines[model_lineno])
  return results

# missing T
def extract_D(document_id, fname):
  lines, lines_idx = lines_index(fname)
  uline = lines[lines_idx['D'][document_id]['line']]
  results = [uline]
  for source_id in lines_idx['D'][document_id]['from']['S']:
    results += _extract_S(source_id, fname, lines, lines_idx, "  ", False)
  return results

def extract_S(snippet_id, fname):
  lines, lines_idx = lines_index(fname)
  return _extract_S(snippet_id, fname, lines, lines_idx, "", True)

# T same as S

# G -> (V & C)
#      -> G wo g0 (recursive)
#      -> A --> U (recursive) --> M
#      -> (S,T) --> D

# A -> (V & C)
#      -> G (recursive)
#      -> A wo A0 --> U (recursive) --> M
#      -> (S,T) --> D

# U ->
#      -> M
#      -> U (recursive)
#      -> A
#         --> C, V
#           --> (S,T) --> D
#      -> G (recursive)

# C, V:
#     -> A
#        --> G (recursive)
#        --> U (recursive) --> M
#        --> (S,T) --> D

def statistics(fname, stats = None):
  lines = collect_lines_with_id(fname)
  if stats is None:
    stats = {'by_record_type': defaultdict(int),
             'total_count': 0,
             'n_G_by_type': defaultdict(int),
             'info_G_by_type': defaultdict(list),
             'n_U_by_type': defaultdict(int),
             'n_A_by_mode': defaultdict(int),
             'n_A_mode_by_U_type': defaultdict(lambda: defaultdict(int)),
             'n_A_by_U': defaultdict(int),
             'U_with_M': set(),
             'n_M_by_resource_id': defaultdict(int),
             'n_V_by_n_sources': defaultdict(int),
             'A_in_V': set(),
             'G_in_V': set(),
             'n_V_by_G_portion': defaultdict(int),
             'n_V_by_operator': defaultdict(int),
             'n_V_by_operator_and_reference': \
                 defaultdict(lambda: defaultdict(int)),
             'n_C_by_n_sources': defaultdict(int),
             'A_in_C': set(),
             'G_in_C': set(),
             'n_C_by_G_portion': defaultdict(int),
             'n_C_by_operator': defaultdict(int),
             'n_C_by_n_A': {1: 0, 2: 0},
             'n_G_defprefix_by_type': defaultdict(lambda: defaultdict(int)),
             'n_G_by_child_type': \
                 defaultdict(lambda: defaultdict(lambda: defaultdict(int))),
             'n_n_A_by_U': defaultdict(int),
             'n_U_with_M': 0,
             'n_A_in_V': 0,
             'n_G_in_V': 0,
             'n_A_in_C': 0,
             'n_G_in_C': 0,
             }

  for line in parsed_lines(fname):

    # (2.1) Total count and by record type
    stats['total_count'] += 1
    stats['by_record_type'][line["record_type"]] += 1

    # (2.2) Statistics by record type

    if line["record_type"] == "G":
      stats['n_G_by_type'][line["type"]] += 1
      if line["type"] not in ['combined', 'taxonomic', 'strain', 'inverted']:
        stats['info_G_by_type'][line["type"]].append(\
            (line['id'], line["name"], line["definition"]))
      if line["type"] not in ["combined", "inverted"]:
        pfx = line["definition"].split(":")[0]
        stats['n_G_defprefix_by_type'][line["type"]][pfx] += 1
      else:
        child_groups = re.findall(r"[a-zA-Z0-9_]+", line["definition"])
        child_types = {g: lines["G"][g]["type"] for g in child_groups}
        while "inverted" in child_types.values() or \
              "combined" in child_types.values():
          to_delete = []
          for g in child_types:
            if child_types[g] in ["inverted", "combined"]:
              child_groups.extend(re.findall(r"[a-zA-Z0-9_]+",
                                             lines["G"][g]["definition"]))
              to_delete.append(g)
          child_groups = [g for g in child_groups if g not in to_delete]
          child_types = {g: lines["G"][g]["type"] for g in child_groups}

        child_types = set(child_types.values())
        if child_types == {"taxonomic"}:
          klass = "only_taxonomic"
        elif "taxonomic" not in child_types:
          klass = "only_not_taxonomic"
        else:
          klass = "mixed"
        key = ",".join(sorted(child_types))
        stats['n_G_by_child_type'][line["type"]][klass][key] += 1

    elif line['record_type'] == "U":
      stats['n_U_by_type'][line["type"]] += 1

    elif line['record_type'] == "A":
      if isinstance(line["mode"], str):
        mkey = line["mode"]
      else:
        mkey = line["mode"]['mode']
      unit = lines['U'][line["unit_id"]]
      stats['n_A_by_mode'][mkey]+= 1
      stats['n_A_mode_by_U_type'][unit['type']][mkey] += 1
      stats['n_A_by_U'][line['unit_id']] += 1

    elif line['record_type'] == "M":
      stats['U_with_M'].add(line['unit_id'])
      stats['n_M_by_resource_id'][line['resource_id']] += 1

    elif line['record_type'] == "V":
      if isinstance(line['source'], str):
        stats['n_V_by_n_sources'][1] += 1
      else:
        stats['n_V_by_n_sources'][len(line['source'])] += 1
      stats['A_in_V'].add(line['attribute'])
      stats['G_in_V'].add(line['group']['id'])
      if 'portion' in line['group']:
        stats['n_V_by_G_portion'][line['group']['portion']] += 1
      else:
        stats['n_V_by_G_portion']['all'] += 1
      stats['n_V_by_operator'][line['operator']] += 1
      stats['n_V_by_operator_and_reference'][\
          line['operator']][line['reference']] += 1

    elif line['record_type'] == "C":
      if isinstance(line['source'], str):
        stats['n_C_by_n_sources'][1] += 1
      else:
        stats['n_C_by_n_sources'][len(line['source'])] += 1
      if isinstance(line['attribute'], str):
        stats['A_in_C'].add(line['attribute'])
        stats['n_C_by_n_A'][1] += 1
      else:
        stats['A_in_C'].add(line['attribute']['id1'])
        stats['A_in_C'].add(line['attribute']['id2'])
        stats['n_C_by_n_A'][2] += 1
      for g in ['group1', 'group2']:
        stats['G_in_C'].add(line[g]['id'])
        if 'portion' in line[g]:
          stats['n_C_by_G_portion'][line[g]['portion']] += 1
        else:
          stats['n_C_by_G_portion']['all'] += 1
      stats['n_C_by_operator'][line['operator']] += 1

  stats['n_U_with_M'] += len(stats['U_with_M'])
  stats['U_with_M'] = set()
  stats['n_A_in_V'] += len(stats['A_in_V'])
  stats['A_in_V'] = set()
  stats['n_G_in_V'] += len(stats['G_in_V'])
  stats['G_in_V'] = set()
  stats['n_A_in_C'] += len(stats['A_in_C'])
  stats['A_in_C'] = set()
  stats['n_G_in_C'] += len(stats['G_in_C'])
  stats['G_in_C'] = set()
  for unit in stats['n_A_by_U']:
    stats['n_n_A_by_U'][stats['n_A_by_U'][unit]] += 1
  stats['n_A_by_U'] = defaultdict(int)
  return stats

from jinja2 import Environment, FileSystemLoader

STATS_REPORT_TEMPLATE = "stats_report.j2"

def stats_report(s):
  env = Environment(loader=FileSystemLoader(str(_data)))
  template = env.get_template(STATS_REPORT_TEMPLATE)
  return template.render(s)

# from https://stackoverflow.com/questions/16259923/
#       how-can-i-escape-latex-special-characters-inside-django-templates
def tex_escape(text):
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

def table(s, fmt, name, **params):
  env = Environment(loader=FileSystemLoader(str(_data)))
  env.filters["texesc"] = tex_escape
  template_filename = f"{fmt}_table_{name}.j2"
  template = env.get_template(template_filename)
  render_params = s.copy()
  render_params.update(params)
  return template.render(render_params)
