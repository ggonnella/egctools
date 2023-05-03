# Methods related to the PGTO which is available as submodule under data

import importlib
import pronto

_data = importlib.resources.files("egctools").joinpath("data")
_pgto_dir = _data.joinpath("pgto")
_pgto_file = _pgto_dir.joinpath("group_type.obo")
PGTO = pronto.Ontology(_pgto_file)

def group_types_info(root_id='GR0000'):
  """
  A list of tuples with information about the terms in 'group_type'
  namespace of the PGTO ontology.

  Return value:
    For each term, it returns a tuple (<EGC_label>, <ID>, <name>).
    Thereby <EGC_label> is the "resource" (i.e. value) associated to the
    "EGC_label" property of the term.
  """
  result = []
  root = PGTO.get(root_id)
  for term in root.subclasses(with_self=False):
    if isinstance(term, pronto.Term):
      if term.namespace == 'group_type':
        egc_lbl = [a.resource for a in term.annotations \
                   if a.property == 'EGC_label'][0]
        result.append((egc_lbl, term.id, term.name))
  return result

def group_type_choices():
  """
  A list of tuples for use in choice fields of web interfaces
  for the terms in namespace 'group_type' of the PGTO.

  Return value:
    For each term, it returns a tuple (<value>, <string>):
    - <value>: "resource" (i.e. value) associated to the "EGC_label"
      property of the term.
    - <string>: term name, preceded by the term ID in parentheses.
  """
  return [(egc_lbl, f"{term_id} ({term_name})") \
      for egc_lbl, term_id, term_name in group_types_info()]

def group_types(root_id='GR0000'):
  """
  A list of EGC labels of the terms in namespace 'group_type' of the PGTO.
  """
  return [egc_lbl for egc_lbl, term_id, term_name in group_types_info(root_id)]

def habitat_group_types():
  return group_types('GH0000')

def phenotype_group_types():
  return group_types('GP0000')

def taxonomy_group_types():
  return group_types('GT0000')

def location_group_types():
  return group_types('GL0000')

def derived_group_types():
  return group_types('GX0000')
