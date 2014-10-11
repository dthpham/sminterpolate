import os
import collections


class SettingsDictionary(collections.MutableMapping):
  '''A dictionary object of a configuration file with key and value
  pairs in the form key=value, with at most one pair on each line.
  Lines starting with a hash (#) are treated as comments.'''
  def __init__(self, *args, **kwargs):
    self.store = dict()
    self.update(dict(*args, **kwargs))
    self.config_path = None

  def __getitem__(self, key):
    return self.store[self.__keytransform__(key)]

  def __setitem__(self, key, value):
    self.store[self.__keytransform__(key)] = value

  def __delitem__(self, key):
    del self.store[self.__keytransform__(key)]

  def __iter__(self):
    return iter(self.store)

  def __len__(self):
    return len(self.store)

  def __keytransform__(self, key):
    return key.lower()

  def save(self):
    if self.config_path is None:
      return
    with open(self.config_path, 'w') as f:
      for k, v in self.iteritems():
        f.write('{}={}\n'.format(k, v))

  @classmethod
  def from_settings_file(cls, path):
    obj = cls()
    obj.config_path = path
    with open(path, 'r') as f:
      for line in f.readlines():
        line = line.strip()
        if line.startswith('#'):
          continue
        if '=' in line:
          k, v = line.split('=')
          obj[k] = v
    return obj

from __init__ import conf_path
if not os.path.exists(conf_path):
  open(conf_path, 'a').close()
settings = SettingsDictionary.from_settings_file(conf_path)
