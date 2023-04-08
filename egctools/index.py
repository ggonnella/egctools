import textformats
from collections import defaultdict
import re
import importlib.resources
from .parser import unparsed_and_parsed_lines
_data = importlib.resources.files("egctools").joinpath("data")
_egcspec = _data.joinpath("egc-spec")
_specfile = _egcspec.joinpath("egc.tf.yaml")
SPEC = textformats.Specification(str(_specfile))

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

def create(fname):
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

