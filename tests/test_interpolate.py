import unittest
from butterflow.motion.interpolate import Interpolate
from butterflow.motion.flow import Flow
import cv2
import os
import numpy as np


class FlowTestCase(unittest.TestCase):
  def setUp(self):
    DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'samples')
    img_1 = os.path.join(DIR, 'img-1280x720-1.png')
    img_2 = os.path.join(DIR, 'img-1280x720-2.png')
    fr_1 = cv2.imread(img_1)
    fr_2 = cv2.imread(img_2)
    fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
    fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)
    self.fu, self.fv = \
        Flow.farneback_optical_flow_ocl(fr_1_gr,fr_2_gr,0.5,3,15,3,7,1.5,0)
    self.bu, self.bv = \
        Flow.farneback_optical_flow_ocl(fr_1_gr,fr_2_gr,0.5,3,15,3,7,1.5,0)
    self.fr_1_32 = np.float32(fr_1)*1/255.0
    self.fr_2_32 = np.float32(fr_2)*1/255.0

    self.ocl_inter_method = lambda(t): \
        Interpolate.interpolate_frames_ocl(
            self.fr_1_32,self.fr_2_32,self.fu, self.fv,self.bu,self.bv, t)

  def test_interpolate_frames_ocl_form(self):
    fr = self.ocl_inter_method(0.5)[0]
    self.assertIsInstance(fr, np.ndarray)
    self.assertEquals(fr.dtype, np.uint8)
    self.assertEquals(len(fr.shape),3)
    r,c,ch = fr.shape
    self.assertEquals(r, 720)
    self.assertEquals(c, 1280)
    self.assertEquals(ch, 3)

  def test_interpolate_frames_ocl_count(self):
    self.assertEquals(len(self.ocl_inter_method(0.500)),1)
    self.assertEquals(len(self.ocl_inter_method(0.250)),4-1)
    self.assertEquals(len(self.ocl_inter_method(0.125)),8-1)
    self.assertEquals(len(self.ocl_inter_method(0.0625)),16-1)

    self.assertEquals(len(self.ocl_inter_method(0.333)),3)
    self.assertEquals(len(self.ocl_inter_method(0.334)),2)

    self.assertEquals(len(self.ocl_inter_method(1)),0)
    with self.assertRaises(ValueError):
      self.assertEquals(len(self.ocl_inter_method(0)),0)

if __name__ == '__main__':
  unittest.main()
