import unittest
import os
from butterflow.project import Project


class ProjectTestCase(unittest.TestCase):
  def setUp(self):
    DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'samples')
    self.test_vid = os.path.join(DIR, 'vid-5s-va.mp4')
    self.proj_out = os.path.join(DIR, 'proj-tmp.json')
    self.proj_invalid = os.path.join(DIR, 'proj-invalid.json')
    self.proj_invalid_ver = os.path.join(DIR, 'proj-bad-ver.json')

  def tearDown(self):
    if os.path.exists(self.proj_out):
      os.remove(self.proj_out)

  def test_create_new_project(self):
    self.assertIsInstance(Project(self.test_vid), Project)

  def test_create_new_project_fails(self):
    with self.assertRaises(ValueError):
      Project('vid-does-not-exist.mp4')

  def test_set_timing_regions_with_string(self):
    p = Project(self.test_vid)
    p.set_timing_regions_with_string('a=00:00:01.5,b=00:00:04.9,fps=48')
    self.assertEquals(len(p.timing_regions),1)
    p.set_timing_regions_with_string(
        'a=00:00:00.5,b=00:00:01.2,fps=48;'
        'a=00:00:02.3,b=00:00:03.3,fps=24000/1001;'
        'a=00:00:03.3,b=00:00:04.999,dur=5')
    self.assertEquals(len(p.timing_regions),3)
    p = Project(self.test_vid)
    p.set_timing_regions_with_string('a=00:00:01.5,b=00:00:04.9,fps=48')
    self.assertEquals(len(p.timing_regions),1)

  def test_set_timing_regions_with_full_string(self):
    p = Project(self.test_vid)
    p.set_timing_regions_with_string('full,fps=48')
    self.assertEquals(len(p.timing_regions),1)
    p.set_timing_regions_with_string('full,dur=5')
    self.assertEquals(len(p.timing_regions),1)
    with self.assertRaises(ValueError):
      p.set_timing_regions_with_string(
          'full,fps=48;'
          'a=00:00:02.3,b=00:00:03.3,fps=24000/1001')
    self.assertEquals(len(p.timing_regions),0)

  @unittest.skip('todo')
  def test_render_video(self):pass

if __name__ == '__main__':
  unittest.main()
