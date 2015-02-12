import unittest
import tempfile
from butterflow.config import Config


class ConfigTestCase(unittest.TestCase):
  def setUp(self):
    config = '''
        # This is a comment
        # This is a comment with an = equal sign
        avutil=ffmpeg\n'''
    self.temp_file = tempfile.NamedTemporaryFile()
    self.temp_file.write(config)
    self.temp_file.flush()
    self.config_file = self.temp_file.name

  def tearDown(self):
    self.temp_file.close()

  def test_dict_from_file(self):
    s = Config.from_file(self.config_file)
    self.assertEquals(len(s), 1)
    self.assertTrue(s['avutil'], 'ffmpeg')

if __name__ == '__main__':
  unittest.main()
