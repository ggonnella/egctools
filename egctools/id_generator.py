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
        "count": "c",
        "complete_count": "c",
        "members_count": "mc",
        "presence": "p",
        "complete_presence": "p",
        "members_presence": "mp",
        "length": "l",
        "average_length": "al",
        "relative_count": "rc",
        "relative_length": "rl",
        None: "x",
      }

GroupTypePfx = {
        # derived
        "combined": "c",
        "inverted": "n",
        # taxon
        "taxonomic": "t",
        "paraphyletic": "pt",
        "strain": "s",
        "metagenome_assembled": "mag",
        # habitat
        "habitat_*": "h",
        "biome": "b",
        "compound_level": "cl",
        "cultiviability": "cv",
        # phenotype
        "primary_metabolism": "pm",
        "metabolic_trait": "m",
        "gram_stain": "gs",
        "taxis": "ts",
        "biointeraction_class": "ic",
        "biointeraction_partner": "ip",
        "biointeraction_outcome": "io",
        # location
        "geographical": "g",
        None: "x",
      }

UnitTypePfx = {
        "amino_acid": "aa",
        "base": "b",
        "family_or_domain": "d",
        "feature_type": "t",
        "function": "f",
        "gene_homologs": "h",
        "protein_homologs": "h",
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
  if gtype.startswith("habitat_"):
    pfx = GroupTypePfx["habitat_*"]
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

