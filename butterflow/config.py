import os


class Config(dict):
  """Works exactly like a dict but can load a config file with key and
  value pairs in the form `key = value` with at most one pair on each line.
  Lines starting with a hash `#` are treated as comments.
  """

  def __init__(self, *args, **kwargs):
    self.update(*args, **kwargs)

  def to_file(self, path):
    with open(path, 'w') as f:
      for k, v in self.iteritems():
        f.write('{}={}\n'.format(k, v))

  @classmethod
  def from_file(cls, path):
    """Returns a Config object updated from kv pairs from a file"""
    obj = cls()
    with open(path, 'r') as f:
      for l in f.readlines():
        l = l.strip()
        if l.startswith('#'):
          continue
        if '=' in l:
          k, v = l.split('=')
          obj[k.lower()] = v.lower()
    return obj

from __init__ import conf_path
if not os.path.exists(conf_path):
  open(conf_path, 'a').close()
settings = Config.from_file(conf_path)
