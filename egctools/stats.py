from collections import defaultdict
import re
import importlib.resources
from .parser import parsed_lines
from jinja2 import Environment, FileSystemLoader
_data = importlib.resources.files("egctools").joinpath("data")
STATS_REPORT_TEMPLATE = "stats_report.j2"

def _lines_with_id(fname):
  lines = defaultdict(dict)
  for line in parsed_lines(fname):
    if 'id' in line:
      rt = line['record_type']
      lines[rt][line['id']] = line
  return lines

def collect(fname, stats = None):
  lines = _lines_with_id(fname)
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

    # Total count and by record type
    stats['total_count'] += 1
    stats['by_record_type'][line["record_type"]] += 1

    # Statistics by record type

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
        if all(t in \
            ["taxonomic", "strain", "paraphyletic", "metagenome_assembled"]
            for t in child_types):
          klass = "only_taxonomic"
        elif all(t not in \
            ["taxonomic", "strain", "paraphyletic", "metagenome_assembled"]
            for t in child_types):
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

def report(s):
  env = Environment(loader=FileSystemLoader(str(_data)))
  template = env.get_template(STATS_REPORT_TEMPLATE)
  return template.render(s)

