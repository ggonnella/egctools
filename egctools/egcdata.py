import os
import hashlib
import shutil
from .parser import unparsed_and_parsed_lines, encode_line
from .references import get_G_to_G, get_U_to_U, get_A_to_U, get_VC_to_ST, \
                        get_VC_to_A, get_VC_to_G
from collections import defaultdict

class EGCData:

    @staticmethod
    def compute_docid_from_pfx_and_item(pfx, item):
      return '-'.join(['D', pfx, item])

    @staticmethod
    def compute_docid(record):
      return EGCData.compute_docid_from_pfx_and_item(\
                            record['document_id']['resource_prefix'],
                            record['document_id']['item'])

    @staticmethod
    def compute_modelid_from_data(unit_id, resource_id, model_id):
      return '-'.join(['M', unit_id, resource_id, model_id])

    @staticmethod
    def compute_modelid(record):
      return EGCData.compute_modelid_from_data(\
          record['unit_id'], record['resource_id'], record['model_id'])

    @staticmethod
    def compute_id(record):
      if record['record_type'] == 'D':
        return EGCData.compute_docid(record)
      elif record['record_type'] == 'M':
        return EGCData.compute_modelid(record)
      else:
        return record['id']

    def _connect(self, rt1, id1, rt2, id2):
      self.graph[rt1][id1]['refs'][rt2].append(id2)
      self.graph[rt2][id2]['ref_by'][rt1].append(id1)

    def _disconnect(self, rt, record_id):
      if rt in self.graph:
        if record_id in self.graph[rt]:
          if 'refs' in self.graph[rt][record_id]:
            for rt2, id2s in self.graph[rt][record_id]['refs'].items():
              for id2 in id2s:
                if 'ref_by' in self.graph[rt2][id2]:
                  if record_id in self.graph[rt2][id2]['ref_by'][rt]:
                    self.graph[rt2][id2]['ref_by'][rt].remove(record_id)
          if 'ref_by' in self.graph[rt][record_id]:
            for rt2, id2s in self.graph[rt][record_id]['ref_by'].items():
              for id2 in id2s:
                if 'refs' in self.graph[rt][record_id]:
                  if record_id in self.graph[rt2][id2]['refs'][rt]:
                    self.graph[rt2][id2]['refs'][rt].remove(record_id)
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
        record_id = self.compute_id(record)
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

    def save_data(self, backup=False):
      if backup:
        backup_file_path = EGCData._get_backup_file_path(self.file_path)
        if not os.path.exists(backup_file_path):
          shutil.copyfile(self.file_path, backup_file_path)

      with open(self.file_path, 'w') as f:
        for line in self.lines:
          if line is not None:
            f.write(line + "\n")

    def create_record(self, record_data):
      record_id = self.compute_id(record_data)
      if record_id in self.id2rnum:
          raise ValueError('Record already exists: {}'.format(record_id))
      self.records.append(record_data)
      self.lines.append(encode_line(record_data))
      record_num = len(self.records) - 1
      self.id2rnum[record_id] = record_num
      rt = record_data["record_type"]
      self.rt2rnums[rt].append(record_num)
      self._graph_add_record(record_id, record_data, True)
      self.save_data()

    def delete_record_by_id(self, record_id):
      if record_id not in self.id2rnum:
          raise ValueError('Record does not exist: {}'.format(record_id))
      record_num = self.id2rnum[record_id]
      record_type = self.records[record_num]["record_type"]
      self.rt2rnums[record_type].remove(record_num)
      self.records[record_num] = None
      self.lines[record_num] = None
      self._disconnect(record_type, record_id)
      del self.id2rnum[record_id]
      self.save_data()

    def delete_record(self, record):
      record_id = self.compute_id(record)
      self.delete_record_by_id(record_id)

    def update_record_by_id(self, existing_id, updated_data):
      if existing_id not in self.id2rnum:
          raise ValueError('Record does not exist: {}'.format(existing_id))
      record_num = self.id2rnum[existing_id]
      updated_id = self.compute_id(updated_data)
      if updated_id != existing_id:
          if updated_id in self.id2rnum:
              raise ValueError('Record already exists: {}'.format(updated_id))
          self.id2rnum[updated_id] = record_num
          del self.id2rnum[existing_id]
      self.records[record_num] = updated_data
      self.lines[record_num] = encode_line(updated_data)
      record_type = updated_data["record_type"]
      self._disconnect(record_type, existing_id)
      self._graph_add_record(updated_id, updated_data, True)
      self.save_data()

    def update_record(self, existing_data, updated_data):
      record_id = self.compute_id(existing_data)
      self.update_record_by_id(record_id, updated_data)

    def get_records(self, record_type):
      return [self.records[i] for i in self.rt2rnums[record_type]]

    def get_record_by_id(self, record_id):
      record_num = self.id2rnum[record_id]
      if record_num is None:
        raise ValueError('Record does not exist: {}'.format(record_id))
      return self.records[record_num]

    def get_record(self, record_data):
      record_id = self.compute_id(record_data)
      return self.get_record_by_id(record_id)

    def has_unique_id(self, record):
      return self.compute_id(record) not in self.id2rnum

    def is_unique_id(self, record_id):
      return record_id not in self.id2rnum

    def id_exists(self, record_id):
      return record_id in self.id2rnum

    def refs_ids(self, rt, record_id, ref_rt):
      return self.graph[rt][record_id]['refs'][ref_rt]

    def ref_by_ids(self, rt, record_id, ref_by_rt):
      return self.graph[rt][record_id]['ref_by'][ref_by_rt]

    def refs(self, rt, record_id, ref_rt):
      return [self.get_record_by_id(ref_id) \
          for ref_id in self.refs_ids(rt, record_id, ref_rt)]

    def ref_by(self, rt, record_id, ref_by_rt):
      return [self.get_record_by_id(ref_by_id) \
          for ref_by_id in self.ref_by_ids(rt, record_id, ref_by_rt)]
