from collections import defaultdict, Counter
import re
import sys
import importlib.resources
from .parser import parsed_lines
from jinja2 import Environment, FileSystemLoader
_data = importlib.resources.files("egctools").joinpath("data")
STATS_REPORT_TEMPLATE = "stats_report.j2"
from . import pgto

# G stats

def _init_G_stats(stats):
  stats['n_G_by_type'] = Counter()
  stats['n_G_by_category'] = Counter()
  stats['n_G_by_category_and_type'] = defaultdict(Counter)
  stats['info_G_by_type'] = defaultdict(list)
  stats['n_G_defprefix_by_type'] = defaultdict(Counter)
  stats['n_G_by_children_type'] = defaultdict(lambda: defaultdict(Counter))
  stats['n_G_by_children_category'] = defaultdict(Counter)

G_categories = {
  'taxonomy': pgto.taxonomy_group_types(),
  'habitat': pgto.habitat_group_types(),
  'phenotype': pgto.phenotype_group_types(),
  'location': pgto.location_group_types(),
  'derived': pgto.derived_group_types(),
}
G_type2category = {}
for category, types in G_categories.items():
  for type in types:
    G_type2category[type] = category

def _collect_G_stats(stats, line, lines):
  type = line['type']
  stats['n_G_by_type'][type] += 1
  category = G_type2category[type]
  stats['n_G_by_category'][category] += 1
  stats['n_G_by_category_and_type'][category][type] += 1
  if category not in ['taxonomy', 'derived']:
    stats['info_G_by_type'][line["type"]].append(\
        (line['id'], line["name"], line["definition"]))
  if category != "derived":
    pfx = line["definition"].split(":")[0]
    stats['n_G_defprefix_by_type'][type][pfx] += 1
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
    child_categories = set(G_type2category[t] for t in child_types)
    if len(child_categories) == 1:
      klass = "{}_category".format(list(child_categories)[0])
    else:
      has_tax = "taxonomy" in child_categories
      child_categories.discard("taxonomy")
      cats = "_".join(sorted(child_categories))
      if has_tax:
        klass = f"taxonomy_and:{cats}"
      else:
        klass = f"no_taxonomy:{cats}"
    key = ",".join(sorted(child_types))
    stats['n_G_by_children_category'][type][klass] += 1
    stats['n_G_by_children_type'][type][klass][key] += 1

# A stats

def _init_A_stats(stats):
  stats['n_A_by_mode'] = Counter()
  stats['n_A_mode_by_U_kind_and_type'] = \
    defaultdict(lambda: defaultdict(Counter))
  stats['n_A_by_U'] = Counter()
  stats['n_n_A_by_U'] = Counter()

def _collect_A_stats(stats, line, lines):
  if isinstance(line["mode"], str):
    mkey = line["mode"]
  else:
    mkey = line["mode"]['mode']
  unit = lines['U'][line["unit_id"]]
  t = unit["type"]
  stats['n_A_by_mode'][mkey]+= 1
  stats['n_A_mode_by_U_kind_and_type'][t['kind']][t['base_type']][mkey] += 1
  stats['n_A_by_U'][line['unit_id']] += 1

def _postprocess_A_stats(stats):
  for unit in stats['n_A_by_U']:
    stats['n_n_A_by_U'][stats['n_A_by_U'][unit]] += 1
  n_units_w_A = len(stats['n_A_by_U'])
  n_units_wo_A = stats['by_record_type']["U"] - n_units_w_A
  stats['n_n_A_by_U'][0] = n_units_wo_A
  stats['n_A_by_U'] = defaultdict(int)

# U stats

def _init_U_stats(stats):
  stats['n_U_by_kind'] = Counter()
  stats['n_U_by_type'] = Counter()
  stats['n_U_by_type_r'] = defaultdict(Counter)
  stats['n_U_by_kind_and_type'] = defaultdict(Counter)
  stats['n_U_by_kind_and_type_r'] = defaultdict(lambda: defaultdict(Counter))

def _collect_U_stats(stats, line, lines):
  t = line['type']
  stats['n_U_by_kind'][t["kind"]] += 1
  stats['n_U_by_type'][t["base_type"]] += 1
  stats['n_U_by_kind_and_type'][t["kind"]][t["base_type"]] += 1
  if 'resource' in t:
    r = t['resource']
    stats['n_U_by_type_r'][t["base_type"]][r] += 1
    stats['n_U_by_kind_and_type_r'][t["kind"]][t["base_type"]][r] += 1

# M stats

def _init_M_stats(stats):
  stats['U_with_M'] = set()
  stats['n_U_with_M'] = 0
  stats['n_M_by_resource_id'] = Counter()

def _collect_M_stats(stats, line, lines):
  stats['U_with_M'].add(line['unit_id'])
  stats['n_M_by_resource_id'][line['resource_id']] += 1

def _postprocess_M_stats(stats):
  stats['n_U_with_M'] = len(stats['U_with_M'])
  stats['U_with_M'] = set()

# V stats

def _init_V_stats(stats):
  stats['n_V_by_n_sources'] = Counter()
  stats['n_V_by_G_portion'] = Counter()
  stats['n_V_by_operator'] = Counter()
  stats['n_V_by_operator_and_reference'] = defaultdict(Counter)
  stats['G_in_V'] = set()
  stats['A_in_V'] = set()
  stats['n_G_in_V'] = 0
  stats['n_A_in_V'] = 0

def _collect_V_stats(stats, line, lines):
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

def _postprocess_V_stats(stats):
  stats['n_A_in_V'] += len(stats['A_in_V'])
  stats['A_in_V'] = set()
  stats['n_G_in_V'] += len(stats['G_in_V'])
  stats['G_in_V'] = set()

# C stats

def _init_C_stats(stats):
  stats['n_C_by_n_sources'] = Counter()
  stats['n_C_by_n_A'] = Counter({1: 0, 2: 0})
  stats['n_C_by_G_portion'] = Counter()
  stats['n_C_by_operator'] = Counter()
  stats['G_in_C'] = set()
  stats['A_in_C'] = set()
  stats['n_A_in_C'] = 0
  stats['n_G_in_C'] = 0

def _collect_C_stats(stats, line, lines):
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

def _postprocess_C_stats(stats):
  stats['n_A_in_C'] += len(stats['A_in_C'])
  stats['A_in_C'] = set()
  stats['n_G_in_C'] += len(stats['G_in_C'])
  stats['G_in_C'] = set()

# common stats

def _init_common_stats(stats):
  stats['by_record_type'] = defaultdict(int)
  stats['total_count'] = 0

def _collect_common_stats(stats, line, lines):
  stats['by_record_type'][line['record_type']] += 1
  stats['total_count'] += 1

# main

def _init_stats():
  stats = {}
  _init_common_stats(stats)
  for rt in ['G', 'A', 'U', 'M', 'V', 'C']:
    if hasattr(sys.modules[__name__], f"_init_{rt}_stats"):
      getattr(sys.modules[__name__], f"_init_{rt}_stats")(stats)
  return stats

def _lines_with_id(fname):
  lines = defaultdict(dict)
  for line in parsed_lines(fname):
    if 'id' in line:
      rt = line['record_type']
      lines[rt][line['id']] = line
  return lines

def collect(fname, stats = None, skip_ids = None):
  lines = _lines_with_id(fname)
  if stats is None:
    stats = _init_stats()
  for line in parsed_lines(fname):
    if skip_ids is not None and 'id' in line:
      if line['id'] in skip_ids:
        continue
      else:
        skip_ids.add(line['id'])
    _collect_common_stats(stats, line, lines)
    rt = line['record_type']
    if hasattr(sys.modules[__name__], f"_collect_{rt}_stats"):
      getattr(sys.modules[__name__], f"_collect_{rt}_stats")(stats, line, lines)
  for rt in stats['by_record_type'].keys():
    if hasattr(sys.modules[__name__], f"_postprocess_{rt}_stats"):
      getattr(sys.modules[__name__], f"_postprocess_{rt}_stats")(stats)
  return stats

def report(s):
  env = Environment(loader=FileSystemLoader(str(_data)))
  template = env.get_template(STATS_REPORT_TEMPLATE)
  return template.render(s, G_categories = G_categories)

