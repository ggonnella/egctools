import textformats
import importlib.resources
from .index import create as create_index
from .parser import parsed_line
_data = importlib.resources.files("egctools").joinpath("data")
_egcspec = _data.joinpath("egc-spec")
_specfile = _egcspec.joinpath("egc.tf.yaml")
SPEC = textformats.Specification(str(_specfile))

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
  lines, lines_idx = create_index(fname)
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
