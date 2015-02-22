import unittest
from butterflow.motion.flow import Flow
import numpy as np
import cv2
import os
import common


class FlowTestCase(unittest.TestCase):
  def setUp(self):
    DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'samples')
    img_1 = os.path.join(DIR, 'img-1280x720-1.png')
    img_2 = os.path.join(DIR, 'img-1280x720-2.png')
    self.fr_1 = cv2.cvtColor(cv2.imread(img_1), cv2.COLOR_BGR2GRAY)
    self.fr_2 = cv2.cvtColor(cv2.imread(img_2), cv2.COLOR_BGR2GRAY)

  def _test_optical_flow_form(self, u, v):
    self.assertIsInstance(u, np.ndarray)
    self.assertIsInstance(v, np.ndarray)
    self.assertEquals(u.dtype, v.dtype)
    self.assertEquals(u.shape, v.shape)
    self.assertEquals(u.dtype, np.float32)
    self.assertEquals(len(u.shape), 2)
    r,c = u.shape
    self.assertEquals(r, 720)
    self.assertEquals(c, 1280)

  def test_hsv_ang_from_flow(self):
    flow = np.zeros((10,10,2), np.float32)
    hsv1 = np.zeros((10,10,3), np.uint8)
    hsv1[...,1] = 255
    hsv1[...,2] = 0
    flow[...,0] = 0
    flow[...,1] = 0
    hsv1[...,0] = np.uint8(0)
    self.assertTrue(np.array_equal(hsv1, Flow.hsv_from_flow(flow)))
    flow[...,0] = 1.0
    flow[...,1] = 1.0
    hsv1[...,0] = np.uint8(45)
    self.assertTrue(np.array_equal(hsv1, Flow.hsv_from_flow(flow)))
    flow[...,0] = 1.0
    flow[...,1] = -1.0
    hsv1[...,0] = np.uint8(315)
    self.assertTrue(np.array_equal(hsv1, Flow.hsv_from_flow(flow)))
    flow[...,0] = -1.0
    flow[...,1] = 1.0
    hsv1[...,0] = np.uint8(135)
    self.assertTrue(np.array_equal(hsv1, Flow.hsv_from_flow(flow)))
    flow[...,0] = -1.0
    flow[...,1] = -1.0
    hsv1[...,0] = np.uint8(225)
    self.assertTrue(np.array_equal(hsv1, Flow.hsv_from_flow(flow)))

  def test_hsv_mag_from_flow(self):
    flow = np.zeros((10,10,2), np.float32)
    hsv1 = np.zeros((10,10,3), np.uint8)
    mag = np.zeros((10,10,1), np.float32)
    hsv1[...,0] = np.uint8(45)
    hsv1[...,1] = 255
    flow[...,0] = 1.0
    flow[...,1] = 1.0
    mag[...] = np.sqrt(np.square(1.0)+np.square(1.0))
    hsv1[...,2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    self.assertTrue(np.array_equal(hsv1, Flow.hsv_from_flow(flow)))
    flow[...,0] = 2.0
    flow[...,1] = 3.5
    mag[...] = np.sqrt(np.square(2.0)+np.square(3.5))
    hsv1[...,2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    hsv1[...,0] = np.uint8(60)
    self.assertTrue(np.array_equal(hsv1, Flow.hsv_from_flow(flow)))

  def test_split_flow_components(self):
    flow = np.zeros((16,9,2), np.float32)
    flow[...,0] = 1.0
    flow[...,1] = 2.0
    u,v = Flow.split_flow_components(flow)
    self.assertTrue(np.array_equal(u, flow[...,0]))
    self.assertTrue(np.array_equal(v, flow[...,1]))

  def test_merge_flow_components(self):
    u = np.zeros((16,9), np.float32)
    v = np.zeros((16,9), np.float32)
    u[...] = 1.0
    v[...] = 2.0
    flow1 = Flow.merge_flow_components(u,v)
    flow2 = np.zeros((16,9,2), np.float32)
    flow2[...,0] = 1.0
    flow2[...,1] = 2.0
    self.assertTrue(np.array_equal(flow1, flow2))

  def test_farneback_optical_flow_form(self):
    '''test if returns a flow field in the right form, doesnt verify values'''
    u,v = Flow.farneback_optical_flow(self.fr_1, self.fr_2,0.5,3,15,3,7,1.5,0)
    self._test_optical_flow_form(u,v)

  def test_farneback_optical_flow_ocl_form(self):
    '''test if returns a flow field in the right form, doesnt verify values'''
    u,v = Flow.farneback_optical_flow_ocl(self.fr_1, self.fr_2,0.5,3,15,3,7,1.5,False,0)
    self._test_optical_flow_form(u,v)

  @unittest.skip('todo')
  def test_farneback_optical_flow_ocl_vs_sw(self):
    '''test if opencl and software versions return the same values'''
    u1,v1 = Flow.farneback_optical_flow_ocl(self.fr_1, self.fr_2,0.5,3,15,3,7,1.5,False,0)
    u2,v2 = Flow.farneback_optical_flow(self.fr_1, self.fr_2,0.5,3,15,3,7,1.5,0)
    self.assertTrue(np.array_equal(u1, u2))
    self.assertTrue(np.array_equal(v1, v2))

  @unittest.skip('todo')
  def test_brox_optical_flow_form(self): pass
  @unittest.skip('todo')
  def test_lucas_kanade_optical_flow(self): pass

if __name__ == '__main__':
  unittest.main()
