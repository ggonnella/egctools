import textformats
from collections import defaultdict
import importlib.resources
from .parser import unparsed_and_parsed_lines
from .references import get_G_to_G, get_U_to_U, get_A_to_U, get_VC_to_ST, \
                        get_VC_to_A, get_VC_to_G

_data = importlib.resources.files("egctools").joinpath("data")
_egcspec = _data.joinpath("egc-spec")
_specfile = _egcspec.joinpath("egc.tf.yaml")
SPEC = textformats.Specification(str(_specfile))

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
      for parent_id in get_G_to_G(line):
        _connect(lines_idx, 'G', line_id, 'G', parent_id)
    elif rt == 'U':
      for parent_id in get_U_to_U(line):
        _connect(lines_idx, 'U', line_id, 'U', parent_id)
    elif rt == 'A':
      for unit_id in get_A_to_U(line):
        _connect(lines_idx, 'A', line_id, 'U', unit_id)
    elif rt == 'M':
      lines_idx['U'][line['unit_id']]['ref_by']['M'].append(i)
    elif rt == 'V' or rt == 'C':
      for source_id in get_VC_to_ST(line):
        lines_idx['S_or_T'][source_id]['ref_by'][rt].append(line_id)
      for attribute_id in get_VC_to_A(line):
        _connect(lines_idx, rt, line_id, 'A', attribute_id)
      for group_id in get_VC_to_G(line):
        _connect(lines_idx, rt, line_id, 'G', group_id)
    i += 1
  for source_id in lines_idx['S_or_T'].keys():
    for rt2 in lines_idx['S_or_T'][source_id]['ref_by']:
      for line_id in lines_idx['S_or_T'][source_id]['ref_by'][rt2]:
        rt = 'S' if source_id in lines_idx['S'] else 'T'
        _connect(lines_idx, rt2, line_id, rt, source_id)
  del lines_idx['S_or_T']
  return lines, lines_idx
