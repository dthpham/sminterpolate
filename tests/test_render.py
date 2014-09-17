import unittest
import os


class RendererTestCase(unittest.TestCase):
  def setUp(self):
    DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'samples')
    self.test_vid = os.path.join(DIR, 'vid-5s-vas.mp4')

  @unittest.skip('todo')
  def tearDown(self):pass
  @unittest.skip('todo')
  def test_init_pipe(self):pass
  @unittest.skip('todo')
  def test_close_pipe(self):pass
  @unittest.skip('todo')
  def test_render(self):pass

if __name__ == '__main__':
  unittest.main()
