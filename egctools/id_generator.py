#
# Auto-generation of unique IDs for the records
#
import re

def _id_ok(egc_data, new_id, old_id):
  return new_id == old_id or not egc_data.id_exists(new_id)

def _add_sfx(egc_data, new_id, old_id):
  sfx = 2
  while True:
    sfx_id = f'{new_id}_{sfx}'
    if _id_ok(egc_data, sfx_id, old_id):
      return sfx_id
    sfx += 1

AttributeModePfx = {
        "complete": "all",
        "conservation": "v",
        "count": "c",
        "members_presence": "mp",
        "presence": "p",
        "relative": "r",
        "relative_length": "rl",
        None: "x",
      }

GroupTypePfx = {
        "requirement": "r",
        "specific_nutrient_availablity": "r",
        "biological_interaction": "i",
        "biological_interaction_partner_taxonomy": "ip",
        "combined": "c",
        "cultiviability": "cv",
        "geographical": "g",
        "gram_stain": "gs",
        "habitat": "h",
        "inverted": "n",
        "metabolic": "m",
        "metagenome_assembled": "ma",
        "paraphyletic": "pt",
        "resultive_disease_symptom": "d",
        "strain": "s",
        "taxis": "x",
        "taxonomic": "t",
        "trophic_strategy": "ts",
        None: "x",
      }

UnitTypePfx = {
        "amino_acid": "aa",
        "base": "b",
        "family_or_domain": "d",
        "feature_type": "t",
        "function": "f",
        "homolog_gene": "h",
        "homolog_protein": "h",
        "ortholog_group": "og",
        "ortholog_groups_category": "k",
        "protein_complex": "pc",
        "specific_gene": "g",
        "specific_protein": "p",
        "gene_cluster": "c",
        "gene_system": "y",
        "metabolic_pathway": "w",
        "genomic_island": "i",
        "trophic_strategy": "ts",
        "unit": "u",
        None: "x",
      }

def _new_id(egc_data, new_id, old_id):
  if _id_ok(egc_data, new_id, old_id):
    return new_id
  else:
    return _add_sfx(egc_data, new_id, old_id)

def _sanitize(s, repl):
  return re.sub(r"[^a-zA-Z0-9_]", repl, s)

def generate_A_id(egc_data, unit_id, mode, old_id=None):
  if unit_id.startswith('U'):
    unit_id = unit_id[1:]
  m = AttributeModePfx.get(mode,
      AttributeModePfx[None]+_sanitize(mode[0:2], ""))
  return _new_id(egc_data, f'A{m}_{unit_id}', old_id)

def generate_G_id(egc_data, name, gtype, old_id=None):
  name = "_".join([_sanitize(n, "")[:5] for n in name.split(" ")])
  if gtype.endswith("_requirement"):
    pfx = GroupTypePfx["requirement"]
  else:
    pfx = GroupTypePfx.get(gtype, GroupTypePfx[None]+gtype[0])
  return _new_id(egc_data, f'G{pfx}_{name}', old_id)

def generate_U_id(egc_data, utype,
                     symbol, definition, description, old_id=None):
  pfx = UnitTypePfx.get(utype, UnitTypePfx[None]+_sanitize(utype[0:2], ""))
  if symbol != ".":
    namesrc = [symbol]
  else:
    namesrc = description.split(" ")
    if definition != ".":
      defparts = definition.split(" ")
      if description == "." or (len(namesrc) > 1 and len(defparts) == 1):
        namesrc = defparts
  namesrc = [_sanitize(n, "_") for n in namesrc]
  if len(namesrc) == 1:
    name = namesrc[0]
  else:
    name = "_".join([n[:5] for n in namesrc if n])

  return _new_id(egc_data, f'U{pfx}_{name}', old_id)

def generate_numbased_id(egc_data, record_type, old_id=None):
  i = 1
  while True:
    new_id = f'{record_type}{i}'
    if _id_ok(egc_data, new_id, old_id):
      return new_id
    i += 1

