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

def update_G_in_G(line, old_id, new_id):
  line['definition'] = re.sub(r"\b%s\b" % old_id, new_id, line['definition'])
  return line

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
  elif line['type'].startswith('ctg!:') or line['type'].startswith('set!:'):
    parent_units = re.findall(r"[a-zA-Z0-9_]+", line["definition"])
  elif line['definition'].startswith('derived:'):
    m = re.match(r'^derived:([a-zA-Z0-9_]+):.*', line['definition'])
    if m:
      parent_units.append(m.group(1))
  return parent_units

def update_U_in_U(line, old_id, new_id):
  line['definition'] = re.sub(r"\b%s\b" % old_id, new_id, line['definition'])
  return line

def get_A_to_U(line):
  units = [line['unit_id']]
  if isinstance(line['mode'], dict) and 'reference' in line['mode']:
    units.append(line['mode']['reference'])
  return units

def update_U_in_A(line, old_id, new_id):
  if line['unit_id'] == old_id:
    line['unit_id'] = new_id
  if isinstance(line['mode'], dict) and 'reference' in line['mode']:
    if line['mode']['reference'] == old_id:
      line['mode']['reference'] = new_id
  return line

def get_VC_to_ST(line):
  if isinstance(line['source'], list):
    return line['source']
  else:
    return [line['source']]

def update_ST_in_VC(line, old_id, new_id):
  if isinstance(line['source'], list):
    line['source'] = [new_id if x == old_id else x for x in line['source']]
  else:
    if line['source'] == old_id:
      line['source'] = new_id
  return line

def get_VC_to_A(line):
  if isinstance(line['attribute'], dict):
    return [line['attribute']['id1'], line['attribute']['id2']]
  else:
    return [line['attribute']]

def update_A_in_VC(line, old_id, new_id):
  if isinstance(line['attribute'], dict):
    if line['attribute']['id1'] == old_id:
      line['attribute']['id1'] = new_id
    if line['attribute']['id2'] == old_id:
      line['attribute']['id2'] = new_id
  else:
    if line['attribute'] == old_id:
      line['attribute'] = new_id
  return line

def get_VC_to_G(line):
  if 'group' in line:
    return [line['group']['id']]
  else:
    return [line['group1']['id'], line['group2']['id']]

def update_G_in_VC(line, old_id, new_id):
  if 'group' in line:
    if line['group']['id'] == old_id:
      line['group']['id'] = new_id
  else:
    if line['group1']['id'] == old_id:
      line['group1']['id'] = new_id
    if line['group2']['id'] == old_id:
      line['group2']['id'] = new_id
  return line

def get_ST_to_D(line):
  document_id_dt = SPEC["external_resource::external_resource_link"]
  return [document_id_dt.encode(line['document_id'])]

def get_M_to_U(line):
  return [line['unit_id']]

def update_U_in_M(line, old_id, new_id):
  line['unit_id'] = new_id
  return line

