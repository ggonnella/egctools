import textformats
import re
import importlib.resources
_data = importlib.resources.files("egctools").joinpath("data")
_egcspec = _data.joinpath("egc-spec")
_specfile = _egcspec.joinpath("egc.tf.yaml")
SPEC = textformats.Specification(str(_specfile))

def get_G_to_G(line):
  parent_groups = []
  if line['type'] == 'combined' or line['type'] == 'inverted':
    parent_groups.extend(re.findall(r"[a-zA-Z0-9_]+", line["definition"]))
  m = re.match(r'^derived:([a-zA-Z0-9_]+):.*', line['definition'])
  if m:
    parent_groups.append(m.group(1))
  return parent_groups

def get_U_to_U(line):
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

def get_A_to_U(line):
  units = [line['unit_id']]
  if isinstance(line['mode'], dict) and 'reference' in line['mode']:
    units.append(line['mode']['reference'])
  return units

def get_VC_to_ST(line):
  if isinstance(line['source'], list):
    return line['source']
  else:
    return [line['source']]

def get_VC_to_A(line):
  if isinstance(line['attribute'], dict):
    return [line['attribute']['id1'], line['attribute']['id2']]
  else:
    return [line['attribute']]

def get_VC_to_G(line):
  if 'group' in line:
    return [line['group']['id']]
  else:
    return [line['group1']['id'], line['group2']['id']]

def get_ST_to_D(line):
  document_id_dt = SPEC["external_resource::external_resource_link"]
  return [document_id_dt.encode(line['document_id'])]

def get_M_to_U(line):
  return [line['unit_id']]

