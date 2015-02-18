import unittest
import tempfile
from butterflow.config import Config


class ConfigTestCase(unittest.TestCase):
  def setUp(self):
    config = (
        '# comment\n'
        '# comment with equal sign =\n'
        'avutil=ffmpeg')
    self.temp_file = tempfile.NamedTemporaryFile()
    self.temp_file.write(config)
    self.temp_file.flush()
    self.config_file = self.temp_file.name

  def tearDown(self):
    self.temp_file.close()

  def test_dict_from_file(self):
    c = Config.from_file(self.config_file)
    self.assertEquals(len(c), 1)
    self.assertTrue(c['avutil'], 'ffmpeg')

  def test_dict_to_file(self):
    c = Config()
    c['k1'] = 'v1'
    c['k2'] = 'v2'
    c.to_file(self.config_file)
    s = (
        'k2=v2\n'
        'k1=v1\n')
    with open(self.config_file, 'r') as f:
      self.assertEquals(s, f.read())

if __name__ == '__main__':
  unittest.main()
