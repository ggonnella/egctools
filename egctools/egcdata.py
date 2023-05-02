import os
import hashlib
import shutil
from .parser import unparsed_and_parsed_lines, encode_line
from .references import get_G_to_G, get_U_to_U, get_A_to_U, get_VC_to_ST, \
                        get_VC_to_A, get_VC_to_G, update_G_in_G, \
                        update_G_in_VC, update_U_in_U, update_U_in_A, \
                        update_U_in_M, update_ST_in_VC, update_A_in_VC
from collections import defaultdict
import pronto
import importlib

class EGCData:
    """
    Represents the data contained in a EGC file.

    An instance is usually created by opening a EGC file using the class method
    EGCData.from_file(filename).

    # Record IDs

    - Each record is assigned an unique ID.
    - If the record has an ID field, the field must contain an ID which
      is unique in the whole file.
    - If the record type has no ID field, the ID is generated by combining
      the record type code with one or multiple fields.
      - D: D-{resource_prefix}-{item}
      - M: M-{unit_id}-{resource_id}-{model_id}
      Since '-' is not allowed in any of the fields, this is a safe way to
      generate unique IDs.

    ## Compute/Parse IDs

    - ``record_id(record)``: Compute the ID for a record
    - ``compose_id(record_type, *fields)``: Compute the ID for a record
      without an ID field
    - ``parse_composed_id(docid)``: Parse a composed ID into its fields

    ## Check IDs

    - ``id_exists(record_id)``: Check if record with that ID already exists
    - ``has_unique_id(record)``: Check if a not-yet-added record has a unique ID

    # Finding records

    - ``find(record_id)``: Get a record by its ID
    - ``line(record_id)``: Get EGC line for a record by its ID
    - ``find_all(record_type)``: Get all records of a given type
    - ``find_all_ids(record_type)``: Get all record IDs of a given type

    # Editing records

    - ``create(record)``: Create a new record from record data
    - ``update(record_id, record)``: Update a record with new data;
      the record_type is not allowed to change
    - ``delete(record_id)``: Delete a record by ID

    # References

    - ``refs_count(record_type, record_id, ref_type)``: Get number of records
      of type ``ref_type`` referenced by a record
    - ``refs(record_type, record_id, ref_type)``: Get all records of type
      ``ref_type`` referenced by a record

    - ``is_ref_by(record_id)``: Check if a record is referenced by other
    - ``ref_by_count(record_type, record_id, ref_type)``: Get number of records
      of type ``ref_type`` referencing a record
    - ``ref_by(record_type, record_id, ref_type)``: Get all records of type
      ``ref_type`` referencing a record

    # File handling

    - ``save(filename)``: Save the data to a file
    - ``save(filename, True)``: Save the data to a file, and create a
      backup of the original file; the name of the backup file is the original
      filename with an hash appended and the extension '.bak'
    """

    @staticmethod
    def parse_composed_id(record_id):
      if record_id.startswith('D-'):
        parts = record_id.split('-', 2)
        if len(parts) != 3:
          raise ValueError('Invalid document ID: {}'.format(record_id))
        return parts[1], parts[2]
      elif record_id.startswith('M-'):
        parts = record_id.split('-', 3)
        if len(parts) != 4:
          raise ValueError('Invalid model ID: {}'.format(record_id))
        return parts[1], parts[2], parts[3]
      else:
        raise ValueError('Invalid composed ID: {}'.format(record_id))

    @staticmethod
    def compute_docid(record):
      return EGCData.compose_id("D", record['document_id']['resource_prefix'],
                                record['document_id']['item'])

    @staticmethod
    def compute_modelid(record):
      return EGCData.compose_id("M",\
          record['unit_id'], record['resource_id'], record['model_id'])

    @staticmethod
    def compose_id(record_type, *id_fields):
      types = {"M": 3, "D": 2}
      if record_type not in types:
        raise ValueError("Unknown record type for composing ID: {}".\
            format(record_type))
      if len(id_fields) != types[record_type]:
        raise ValueError("Wrong number of ID fields for composing an ID of"+\
            "a record of type {}: {}".\
            format(record_type, len(id_fields)))
      return '-'.join([record_type]+list(id_fields))

    @staticmethod
    def record_id(record):
      if record['record_type'] == 'D':
        return EGCData.compute_docid(record)
      elif record['record_type'] == 'M':
        return EGCData.compute_modelid(record)
      else:
        return record['id']

    def _connect(self, rt1, id1, rt2, id2):
      self.graph[rt1][id1]['refs'][rt2].append(id2)
      self.graph[rt2][id2]['ref_by'][rt1].append(id1)

    def _update_reference(self, record_id, record_type,
                          ref_type, ref_old_id, ref_new_id):
      record_num = self.id2rnum[record_id]
      record = self.records[record_num]
      if ref_type == 'U':
        if record_type == 'U':
          update_U_in_U(record, ref_old_id, ref_new_id)
        elif record_type == 'A':
          update_U_in_A(record, ref_old_id, ref_new_id)
        elif record_type == 'M':
          update_U_in_M(record, ref_old_id, ref_new_id)
          new_M_id = self.record_id(record)
          self.id2rnum[new_M_id] = self.id2rnum[record_id]
          del self.id2rnum[record_id]
          self.graph['M'][new_M_id] = self.graph['M'][record_id]
          del self.graph['M'][record_id]
          self.graph['U'][ref_old_id]['ref_by']['M'].remove(record_id)
          self.graph['U'][ref_old_id]['ref_by']['M'].append(new_M_id)
        else:
          assert False
      elif ref_type in ['S', 'T']:
        if record_type in ['V', 'C']:
          update_ST_in_VC(record, ref_old_id, ref_new_id)
        else:
          assert False
      elif ref_type == 'A':
        if record_type in ['V', 'C']:
          update_A_in_VC(record, ref_old_id, ref_new_id)
        else:
          assert False
      elif ref_type == 'G':
        if record_type in ['V', 'C']:
          update_G_in_VC(record, ref_old_id, ref_new_id)
        elif record_type == 'G':
          update_G_in_G(record, ref_old_id, ref_new_id)
        else:
          assert False
      elif ref_type == 'D':
        assert record_type in ['S', 'T']
        pfx, item = self.parse_composed_id(ref_new_id)
        record['document_id']['item'] = item
        record['document_id']['resource_prefix'] = pfx
      self.lines[record_num] = encode_line(record)
      return self.record_id(record)

    def _disconnect(self, rt, record_id):
      for rt2, id2s in self.graph[rt][record_id]['refs'].items():
        for id2 in id2s:
          if 'ref_by' in self.graph[rt2][id2]:
            if record_id in self.graph[rt2][id2]['ref_by'][rt]:
              self.graph[rt2][id2]['ref_by'][rt].remove(record_id)
      for rt2, id2s in self.graph[rt][record_id]['ref_by'].items():
        for id2 in id2s:
          if 'refs' in self.graph[rt][record_id]:
            if record_id in self.graph[rt2][id2]['refs'][rt]:
              self.graph[rt2][id2]['refs'][rt].remove(record_id)
      del self.graph[rt][record_id]

    def _disconnect_ref_and_update_ref_by(self, rt, record_id, new_record_id):
      for rt2, id2s in self.graph[rt][record_id]['refs'].items():
        for id2 in id2s:
          if 'ref_by' in self.graph[rt2][id2]:
            if record_id in self.graph[rt2][id2]['ref_by'][rt]:
              self.graph[rt2][id2]['ref_by'][rt].remove(record_id)
      self.graph[rt][record_id]['refs'] = defaultdict(list)
      if new_record_id != record_id:
        for rt2, in self.graph[rt][record_id]['ref_by'].keys():
          ref_by_ids = list(self.graph[rt][record_id]['ref_by'][rt2])
          for id2 in ref_by_ids:
            if 'refs' in self.graph[rt2][id2]:
              if record_id in self.graph[rt2][id2]['refs'][rt]:
                  new_id2 = self._update_reference(id2, rt2,
                                         rt, record_id, new_record_id)
                  self.graph[rt2][new_id2]['refs'][rt].remove(record_id)
                  self.graph[rt2][new_id2]['refs'][rt].append(new_record_id)
        self.graph[rt][new_record_id] = self.graph[rt][record_id]
        del self.graph[rt][record_id]

    def _graph_add_S(self, record_id, record):
      document_id = self.compute_docid(record)
      self._connect('S', record_id, 'D', document_id)

    def _graph_add_T(self, record_id, record):
      document_id = self.compute_docid(record)
      self._connect('T', record_id, 'D', document_id)

    def _graph_add_G(self, record_id, record):
      for parent_id in get_G_to_G(record):
        self._connect('G', record_id, 'G', parent_id)

    def _graph_add_U(self, record_id, record):
      for parent_id in get_U_to_U(record):
        self._connect('U', record_id, 'U', parent_id)

    def _graph_add_A(self, record_id, record):
      for unit_id in get_A_to_U(record):
        self._connect('A', record_id, 'U', unit_id)

    def _graph_add_M(self, record_id, record):
      self._connect('M', record_id, 'U', record['unit_id'])

    def _graph_add_VC(self, rt, record_id, record):
      for source_id in get_VC_to_ST(record):
        self.graph['S_or_T'][source_id]['ref_by'][rt].append(record_id)
      for attribute_id in get_VC_to_A(record):
        self._connect(rt, record_id, 'A', attribute_id)
      for group_id in get_VC_to_G(record):
        self._connect(rt, record_id, 'G', group_id)

    def _graph_add_V(self, record_id, record):
      self._graph_add_VC('V', record_id, record)

    def _graph_add_C(self, record_id, record):
      self._graph_add_VC('C', record_id, record)

    def _graph_add_D(self, record_id, record):
      pass

    def _graph_solve_VC_ST(self):
      for source_id in self.graph['S_or_T'].keys():
        for rt2 in self.graph['S_or_T'][source_id]['ref_by']:
          for record_id in self.graph['S_or_T'][source_id]['ref_by'][rt2]:
            rt = 'S' if source_id in self.graph['S'] else 'T'
            self._connect(rt2, record_id, rt, source_id)
      del self.graph['S_or_T']

    def _graph_add_record(self, record_id, record, solve_VC_ST = False):
      rt = record['record_type']
      getattr(self, '_graph_add_' + rt)(record_id, record)
      if solve_VC_ST:
        self._graph_solve_VC_ST()

    def _create_index(self):
      for i, record in enumerate(self.records):
        rt = record['record_type']
        self.rt2rnums[rt].append(i)
        record_id = self.record_id(record)
        self.id2rnum[record_id] = i
        self._graph_add_record(record_id, record)
      self._graph_solve_VC_ST()

    def __init__(self, file_path, records = [], lines = []):
        self.file_path = file_path
        self.records = records
        self.lines = lines
        if len(lines) != len(records):
          raise ValueError('Number of lines does not match number of records')
        self.id2rnum = {}
        self.rt2rnums = defaultdict(list)
        self.graph = defaultdict(\
                lambda: defaultdict(lambda: {
                           'ref_by': defaultdict(list),
                           'refs': defaultdict(list)}))
        if len(records) > 0:
          self._create_index()

    @classmethod
    def from_file(cls, file_path, backup=False):
        if not os.path.exists(file_path):
          raise FileNotFoundError('File not found: {}'.format(file_path))
        records = []
        lines = []
        for unparsed, parsed in unparsed_and_parsed_lines(file_path):
          lines.append(unparsed)
          records.append(parsed)
        if backup:
          backup_file_path = EGCData._get_backup_file_path(file_path)
          if not os.path.exists(backup_file_path):
            shutil.copyfile(file_path, backup_file_path)
        return cls(file_path, records, lines)

    @staticmethod
    def _get_backup_file_path(file_path, prefix_length=8):
      # Calculate the hash of the original file content
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
          hasher.update(f.read())
        hash_prefix = hasher.hexdigest()[:prefix_length]

        # Construct the backup file path
        backup_file_path = f"{file_path}.{hash_prefix}.bak"
        return backup_file_path

    def save(self, backup=False):
      if backup:
        backup_file_path = EGCData._get_backup_file_path(self.file_path)
        if not os.path.exists(backup_file_path):
          shutil.copyfile(self.file_path, backup_file_path)

      with open(self.file_path, 'w') as f:
        for line in self.lines:
          if line is not None:
            f.write(line + "\n")

    def create(self, record_data):
      record_id = self.record_id(record_data)
      if record_id in self.id2rnum:
          raise ValueError('Record already exists: {}'.format(record_id))
      self.records.append(record_data)
      self.lines.append(encode_line(record_data))
      record_num = len(self.records) - 1
      self.id2rnum[record_id] = record_num
      rt = record_data["record_type"]
      self.rt2rnums[rt].append(record_num)
      self._graph_add_record(record_id, record_data, True)

    def delete(self, record_id):
      if record_id not in self.id2rnum:
          raise ValueError('Record does not exist: {}'.format(record_id))
      record_num = self.id2rnum[record_id]
      record_type = self.records[record_num]["record_type"]
      self.rt2rnums[record_type].remove(record_num)
      self.records[record_num] = None
      self.lines[record_num] = None
      self._disconnect(record_type, record_id)
      del self.id2rnum[record_id]

    def update(self, existing_id, updated_data):
      if existing_id not in self.id2rnum:
          raise ValueError('Record does not exist: {}'.format(existing_id))
      record_num = self.id2rnum[existing_id]
      record_type = self.records[record_num]["record_type"]
      if record_type != updated_data["record_type"]:
          raise ValueError('Record type cannot be changed')
      updated_id = self.record_id(updated_data)
      if updated_id != existing_id:
          if updated_id in self.id2rnum:
              raise ValueError('Record already exists: {}'.format(updated_id))
          self.id2rnum[updated_id] = record_num
          del self.id2rnum[existing_id]
      self.records[record_num] = updated_data
      self.lines[record_num] = encode_line(updated_data)
      record_type = updated_data["record_type"]
      self._disconnect_ref_and_update_ref_by(\
          record_type, existing_id, updated_id)
      self._graph_add_record(updated_id, updated_data, True)

    def find_all(self, record_type):
      return [self.records[i] for i in self.rt2rnums[record_type]]

    def find_all_ids(self, record_type):
      return [self.record_id(self.records[i]) \
          for i in self.rt2rnums[record_type]]

    def find(self, record_id):
      record_num = self.id2rnum[record_id]
      if record_num is None:
        raise ValueError('Record does not exist: {}'.format(record_id))
      return self.records[record_num]

    def line(self, record_id):
      record_num = self.id2rnum[record_id]
      return self.lines[record_num]

    def get_record(self, record_data):
      record_id = self.record_id(record_data)
      return self.find(record_id)

    def has_unique_id(self, record):
      return self.record_id(record) not in self.id2rnum

    def id_exists(self, record_id):
      return record_id in self.id2rnum

    def _refs_ids(self, rt, record_id, ref_rt):
      return self.graph[rt][record_id]['refs'][ref_rt]

    def _ref_by_ids(self, rt, record_id, ref_by_rt):
      return self.graph[rt][record_id]['ref_by'][ref_by_rt]

    def refs(self, rt, record_id, ref_rt):
      return [self.find(ref_id) \
          for ref_id in self._refs_ids(rt, record_id, ref_rt)]

    def refs_count(self, rt, record_id, ref_rt):
      return len(self._refs_ids(rt, record_id, ref_rt))

    def ref_by(self, rt, record_id, ref_by_rt):
      return [self.find(ref_by_id) \
          for ref_by_id in self._ref_by_ids(rt, record_id, ref_by_rt)]

    def ref_by_count(self, rt, record_id, ref_by_rt):
      return len(self._ref_by_ids(rt, record_id, ref_by_rt))

    def is_ref_by(self, record_id):
      record = self.records[self.id2rnum[record_id]]
      rt = record['record_type']
      if rt in self.graph:
        if record_id in self.graph[rt]:
          if 'ref_by' in self.graph[rt][record_id]:
            for rt2 in self.graph[rt][record_id]['ref_by']:
              if self.graph[rt][record_id]['ref_by'][rt2]:
                return True
      return False

    _data = importlib.resources.files("egctools").joinpath("data")
    _pgto_dir = _data.joinpath("pgto")
    _pgto_file = _pgto_dir.joinpath("group_type.obo")
    _pgto = pronto.Ontology(_pgto_file)

    @staticmethod
    def pgto_types():
      return [(term.id, term.name) for term in EGCData._pgto.values() if
          isinstance(term, pronto.Term) and term.namespace == 'group_type']
