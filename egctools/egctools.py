import textformats
from collections import defaultdict
import re
import importlib.resources
_data = importlib.resources.files("egctools").joinpath("data")
_egcspec = _data.joinpath("egc-spec")
_specfile = _egcspec.joinpath("egc.tf.yaml")
SPEC = textformats.Specification(str(_specfile))
STATS_REPORT_TEMPLATE = "stats_report.j2"

def parsed_line(s):
  elements = SPEC["line"].decode(s.rstrip("\n"))
  return elements

def parsed_lines(fname):
  for line in open(fname):
    yield parsed_line(line)

def statistics(fname, stats = None):

  # (1) Collect lines by record type and ID
  lines = {}
  for line in parsed_lines(fname):
    if 'id' in line:
      if line['record_type'] not in lines:
        lines[line['record_type']] = {}
      lines[line['record_type']][line['id']] = line

  # (2) Collect statistics
  if stats is None:
    stats = {'by_record_type': defaultdict(int),
             'total_count': 0,
             'n_G_by_type': defaultdict(int),
             'info_G_by_type': defaultdict(list),
             'n_U_by_type': defaultdict(int),
             'n_A_by_mode': defaultdict(int),
             'n_A_mode_by_U_type': defaultdict(lambda: defaultdict(int)),
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
             'n_G_by_child_type': defaultdict(lambda: defaultdict(int)),
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
            (line["name"], line["definition"]))
      if line["type"] not in ["combined", "inverted"]:
        pfx = line["definition"].split(":")[0]
        stats['n_G_defprefix_by_type'][line["type"]][pfx] += 1
      else:
        # extract the identifiers from combined and inverted
        # then go to each group and check the type
        # then count the combinations in a dict
        # (1) extract the identifiers, made of letters, digits and underscores
        child_groups = re.findall(r"[a-zA-Z0-9_]+", line["definition"])
        # (2) go to each group and check the type
        child_types = set(lines["G"][g]["type"] for g in child_groups)
        # (3) count the combinations in a dict
        key = ",".join(sorted(child_types))
        stats['n_G_by_child_type'][line["type"]][key] += 1

    elif line['record_type'] == "U":
      stats['n_U_by_type'][line["type"]] += 1

    elif line['record_type'] == "A":
      mkey = str(line['mode'])
      unit = lines['U'][line["unit_id"]]
      stats['n_A_by_mode'][mkey]+= 1
      stats['n_A_mode_by_U_type'][unit['type']][mkey] += 1

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

  stats['n_U_with_M'] = len(stats['U_with_M'])
  del stats['U_with_M']
  stats['n_A_in_V'] = len(stats['A_in_V'])
  del stats['A_in_V']
  stats['n_G_in_V'] = len(stats['G_in_V'])
  del stats['G_in_V']
  stats['n_A_in_C'] = len(stats['A_in_C'])
  del stats['A_in_C']
  stats['n_G_in_C'] = len(stats['G_in_C'])
  del stats['G_in_C']
  return stats

from jinja2 import Environment, FileSystemLoader

def stats_report(s):
  env = Environment(loader=FileSystemLoader(str(_data)))
  template = env.get_template(STATS_REPORT_TEMPLATE)
  return template.render(s)
