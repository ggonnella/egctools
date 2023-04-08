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

def encode_line(data):
  return SPEC["line"].encode(data)

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

def _find_G_parents(line):
  parent_groups = []
  if line['type'] == 'combined' or line['type'] == 'inverted':
    parent_groups.extend(re.findall(r"[a-zA-Z0-9_]+", line["definition"]))
  m = re.match(r'^derived:([a-zA-Z0-9_]+):.*', line['definition'])
  if m:
    parent_groups.append(m.group(1))
  return parent_groups

def _find_U_parents(line):
  parent_units = []
  if line['type'].startswith('homolog_'):
    m = re.match(r'^homolog:([a-zA-Z0-9_]+)', line['definition'])
    if m:
      parent_units.append(m.group(1))
  elif line['type'] == 'set!:arrangement':
    parts = line['definition'].split(',')
    for part in parts:
      m = re.match(r'^([a-zA-Z0-9_]+)$', part)
      if m:
        parent_units.append(m.group(1))
  elif line['type'].startswith('*') or line['type'].startswith('set!:'):
    parent_units = re.findall(r"[a-zA-Z0-9_]+", line["definition"])
  return parent_units

def _find_A_units(line):
  units = [line['unit_id']]
  if isinstance(line['mode'], dict) and 'reference' in line['mode']:
    units.append(line['mode']['reference'])
  return units

def _find_VC_sources(line):
  if isinstance(line['source'], list):
    return line['source']
  else:
    return [line['source']]

def _find_VC_attributes(line):
  if isinstance(line['attribute'], dict):
    return [line['attribute']['id1'], line['attribute']['id2']]
  else:
    return [line['attribute']]

def _find_VC_groups(line):
  if 'group' in line:
    return [line['group']['id']]
  else:
    return [line['group1']['id'], line['group2']['id']]

def _connect(lines_idx, rt1, id1, rt2, id2):
  lines_idx[rt1][id1]['refs'][rt2].append(id2)
  lines_idx[rt2][id2]['ref_by'][rt1].append(id1)

def lines_index(fname):
  lines = []
  lines_idx = defaultdict(\
                lambda: defaultdict(\
                  lambda: {'line': None,
                           'ref_by': defaultdict(list),
                           'refs': defaultdict(list)}))
  i = 0
  for uline, line in unparsed_and_parsed_lines(fname):
    lines.append(uline)
    rt = line['record_type']
    if 'id' in line:
      line_id = line['id']
      lines_idx[rt][line_id]['line'] = i
    if 'document_id' in line:
      document_id_dt = SPEC["external_resource::external_resource_link"]
      document_id = document_id_dt.encode(line['document_id'])
    if rt == 'D':
      lines_idx["D"][document_id]['line'] = i
    elif rt == 'S' or rt == 'T':
      _connect(lines_idx, rt, line_id, 'D', document_id)
    elif rt == 'G':
      for parent_id in _find_G_parents(line):
        _connect(lines_idx, 'G', line_id, 'G', parent_id)
    elif rt == 'U':
      for parent_id in _find_U_parents(line):
        _connect(lines_idx, 'U', line_id, 'U', parent_id)
    elif rt == 'A':
      for unit_id in _find_A_units(line):
        _connect(lines_idx, 'A', line_id, 'U', unit_id)
    elif rt == 'M':
      lines_idx['U'][line['unit_id']]['ref_by']['M'].append(i)
    elif rt == 'V' or rt == 'C':
      for source_id in _find_VC_sources(line):
        lines_idx['S_or_T'][source_id]['ref_by'][rt].append(line_id)
      for attribute_id in _find_VC_attributes(line):
        _connect(lines_idx, rt, line_id, 'A', attribute_id)
      for group_id in _find_VC_groups(line):
        _connect(lines_idx, rt, line_id, 'G', group_id)
    i += 1
  for source_id in lines_idx['S_or_T'].keys():
    for rt2 in lines_idx['S_or_T'][source_id]['ref_by']:
      for line_id in lines_idx['S_or_T'][source_id]['ref_by'][rt2]:
        rt = 'S' if source_id in lines_idx['S'] else 'T'
        _connect(lines_idx, rt2, line_id, rt, source_id)
  del lines_idx['S_or_T']
  return lines, lines_idx

def _extract_V_or_C(rule_rt, rule_id, lines, lines_idx, skip, indent, indented,
                    numbered, follow_G, exclude_G_id, follow_A, exclude_A_id,
                    follow_ST):
  n = lines_idx[rule_rt][rule_id]['line']
  nstr = f"[{n+1}]\t" if numbered else ""
  results = [nstr + indent + lines[n]]
  skip.append(rule_id)
  indent1 = indent + "  " if indented else ""
  if follow_G:
    for group_id in lines_idx[rule_rt][rule_id]['refs']['G']:
      if group_id != exclude_G_id and group_id not in skip:
        results.extend(_extract_G(group_id, lines, lines_idx, skip,
                indent1, indented, numbered, True, False, exclude_G_id, False))
  if follow_A:
    for attr_id in lines_idx[rule_rt][rule_id]['refs']['A']:
      if attr_id != exclude_A_id and attr_id not in skip:
        results.extend(_extract_A(attr_id, lines, lines_idx, skip,
                            indent1, indented, numbered, True, None, False))
  if follow_ST:
    for source_rt in ['S', 'T']:
      for source_id in lines_idx[rule_rt][rule_id]['refs'][source_rt]:
        if source_id not in skip:
          results.extend(_extract_S_or_T(source_rt, source_id, lines, lines_idx,
            skip, indent1, indented, numbered, True, False))
  return results

def _extract_S_or_T(source_rt, source_id, lines, lines_idx, skip, indent,
                    indented, numbered, follow_D, climb_VC):
  n = lines_idx[source_rt][source_id]['line']
  nstr = f"[{n+1}]\t" if numbered else ""
  results = [nstr + indent + lines[n]]
  skip.append(source_id)
  line = parsed_line(lines[n])
  document_id_dt = SPEC["external_resource::external_resource_link"]
  document_id = document_id_dt.encode(line['document_id'])
  indent1 = indent + "  " if indented else ""
  if follow_D:
    if document_id not in skip:
      results.extend(_extract_D(document_id, lines, lines_idx, skip,
                                indent1, indented, numbered, False))
  if climb_VC:
    for rt in ['V', 'C']:
      for line_id in lines_idx[source_rt][source_id]['ref_by'][rt]:
        if line_id not in skip:
          results.extend(_extract_V_or_C(rt, line_id, lines, lines_idx, skip,
            indent1, indented, numbered, True, None, True, None, False))
  return results

def _extract_A(attr_id, lines, lines_idx, skip, indent, indented, numbered,
               follow_U, exclude_U_id, climb_VC):
  n = lines_idx['A'][attr_id]['line']
  nstr = f"[{n+1}]\t" if numbered else ""
  results = [nstr + indent + lines[n]]
  skip.append(attr_id)
  indent1 = indent + "  " if indented else ""
  if follow_U:
    for unit_id in lines_idx['A'][attr_id]['refs']['U']:
      if unit_id != exclude_U_id and unit_id not in skip:
        results.extend(_extract_U(unit_id, lines, lines_idx, skip, indent1,
                indented, numbered, True, False, exclude_U_id, True, False))
  if climb_VC:
    for rt in ['V', 'C']:
      for line_id in lines_idx['A'][attr_id]['ref_by'][rt]:
        if line_id not in skip:
          results.extend(_extract_V_or_C(rt, line_id, lines, lines_idx, skip,
            indent1, indented, numbered, True, None, True, attr_id, True))
  return results

def _extract_recursively(rt, line_id, lines, lines_idx, skip, indent, indented,
                         numbered, follow_M, exclude_id, direction):
  results = []
  stack = [(ln, indent) for ln in lines_idx[rt][line_id][direction][rt]]
  while len(stack) > 0:
    line2_id, indent1 = stack.pop()
    if line2_id not in skip:
      n = lines_idx[rt][line2_id]['line']
      nstr = f"[{n+1}]\t" if numbered else ""
      results.append(nstr + indent1 + lines[n])
      skip.append(line2_id)
      indent2 = indent1 + "  " if indented else ""
      if follow_M:
        for model_lineno in lines_idx[rt][line2_id]['ref_by']['M']:
          nstr = f"[{model_lineno+1}]\t" if numbered else ""
          results.append(nstr + indent2 + lines[model_lineno])
      for line3_id in lines_idx[rt][line2_id][direction][rt]:
        if line3_id not in skip and line3_id != exclude_id:
          stack.append((line3_id, indent2))
  return results

def _extract_U(unit_id, lines, lines_idx, skip, indent, indented, numbered,
               follow_U, climb_U, exclude_U_id, follow_M, climb_A):
  n = lines_idx['U'][unit_id]['line']
  nstr = f"[{n+1}]\t" if numbered else ""
  results = [nstr + indent + lines[n]]
  indent1 = indent + "  " if indented else ""
  skip.append(unit_id)
  if follow_M:
    for model_lineno in lines_idx['U'][unit_id]['ref_by']['M']:
      nstr = f"[{model_lineno+1}]\t" if numbered else ""
      results.append(nstr + indent1 + lines[model_lineno])
  if follow_U:
    results.extend(_extract_recursively('U', unit_id, lines, lines_idx, skip,
                indent1, indented, numbered, follow_M, exclude_U_id, 'refs'))
  if climb_U:
    results.extend(_extract_recursively('U', unit_id, lines, lines_idx, skip,
                indent1, indented, numbered, follow_M, exclude_U_id, 'ref_by'))
  if climb_A:
    for attr_id in lines_idx['U'][unit_id]['ref_by']['A']:
      if attr_id not in skip:
        results.extend(_extract_A(attr_id, lines, lines_idx, skip, indent1,
          indented, numbered, True, unit_id, True))
  return results

def _extract_G(group_id, lines, lines_idx, skip, indent, indented, numbered,
               follow_G, climb_G, exclude_G_id, climb_VC):
  n = lines_idx['G'][group_id]['line']
  nstr = f"[{n+1}]\t" if numbered else ""
  results = [nstr + indent + lines[n]]
  skip.append(group_id)
  indent1 = indent + "  " if indented else ""
  if follow_G:
    results.extend(_extract_recursively('G', group_id, lines, lines_idx, skip,
                     indent1, indented, numbered, False, exclude_G_id, 'refs'))
  if climb_G:
    results.extend(_extract_recursively('G', group_id, lines, lines_idx, skip,
                indent1, indented, numbered, False, exclude_G_id, 'ref_by'))
  if climb_VC:
    for rt in ['V', 'C']:
      for line_id in lines_idx['G'][group_id]['ref_by'][rt]:
        if line_id not in skip:
          results.extend(_extract_V_or_C(rt, line_id, lines, lines_idx, skip,
            indent1, indented, numbered, False, group_id, True, None, True))
  return results

def _extract_D(document_id, lines, lines_idx, skip, indent, indented, numbered,
              climb_ST):
  n = lines_idx['D'][document_id]['line']
  nstr = f"[{n+1}]\t" if numbered else ""
  results = [nstr + indent + lines[n]]
  skip.append(document_id)
  indent1 = indent + "  " if indented else ""
  if climb_ST:
    for source_rt in ['S', 'T']:
      for source_id in lines_idx['D'][document_id]['ref_by'][source_rt]:
        if source_id not in skip:
          results += _extract_S_or_T(source_rt, source_id, lines,
              lines_idx, skip, indent1, indented, numbered, False, True)
  return results

def extract(line_id, fname, indented, numbered):
  lines, lines_idx = lines_index(fname)
  if line_id in lines_idx['D']:
    return _extract_D(line_id, lines, lines_idx, [],
                      "", indented, numbered, True)
  elif line_id in lines_idx['S']:
    return _extract_S_or_T('S', line_id, lines, lines_idx, [],
                           "", indented, numbered, True, True)
  elif line_id in lines_idx['T']:
    return _extract_S_or_T('T', line_id, lines, lines_idx, [],
                           "", indented, numbered, True, True)
  elif line_id in lines_idx['G']:
    return _extract_G(line_id, lines, lines_idx, [],
                      "", indented, numbered, True, True, None, True)
  elif line_id in lines_idx['A']:
    return _extract_A(line_id, lines, lines_idx, [],
                      "", indented, numbered, True, None, True)
  elif line_id in lines_idx['U']:
    return _extract_U(line_id, lines, lines_idx, [],
                      "", indented, numbered, True, True, line_id, True,
        True)
  elif line_id in lines_idx['V']:
    return _extract_V_or_C('V', line_id, lines, lines_idx, [],
                           "", indented, numbered, True, None, True, None, True)
  elif line_id in lines_idx['C']:
    return _extract_V_or_C('C', line_id, lines, lines_idx, [],
                           "", indented, numbered, True, None, True, None, True)
  raise ValueError("Unknown line ID: " + line_id)

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
