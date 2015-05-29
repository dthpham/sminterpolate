import unittest
import os
import cv2
import numpy as np
from butterflow.flow import hsv_from_flow, split_flow_components, \
    merge_flow_components

SDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                    'samples')

# flows are represented as numpy.ndarrays of type np.float32 with 3 dimensions
# and 2 channels, one each for the `u` horizontal and `v` vertical components.
# Each component defines the displacement at every point in an image.

class FlowTestCase(unittest.TestCase):
    def setUp(self):
        img_1 = os.path.join(SDIR, 'img-1280x720-1.png')
        img_2 = os.path.join(SDIR, 'img-1280x720-2.png')
        self.fr_1 = cv2.cvtColor(cv2.imread(img_1), cv2.COLOR_BGR2GRAY)
        self.fr_2 = cv2.cvtColor(cv2.imread(img_2), cv2.COLOR_BGR2GRAY)

    def test_hsv_ang_from_flow(self):
        flow = np.zeros((10,10,2), np.float32)
        hsv1 = np.zeros((10,10,3), np.uint8)
        hsv1[...,1] = 255
        hsv1[...,2] = 0
        flow[...,0] = 0
        flow[...,1] = 0
        hsv1[...,0] = np.uint8(0)
        self.assertTrue(np.array_equal(hsv1, hsv_from_flow(flow)))
        flow[...,0] = 1.0
        flow[...,1] = 1.0
        hsv1[...,0] = np.uint8(45)
        self.assertTrue(np.array_equal(hsv1, hsv_from_flow(flow)))
        flow[...,0] = 1.0
        flow[...,1] = -1.0
        hsv1[...,0] = np.uint8(315)
        self.assertTrue(np.array_equal(hsv1, hsv_from_flow(flow)))
        flow[...,0] = -1.0
        flow[...,1] = 1.0
        hsv1[...,0] = np.uint8(135)
        self.assertTrue(np.array_equal(hsv1, hsv_from_flow(flow)))
        flow[...,0] = -1.0
        flow[...,1] = -1.0
        hsv1[...,0] = np.uint8(225)
        self.assertTrue(np.array_equal(hsv1, hsv_from_flow(flow)))

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
        self.assertTrue(np.array_equal(hsv1, hsv_from_flow(flow)))
        flow[...,0] = 2.0
        flow[...,1] = 3.5
        mag[...] = np.sqrt(np.square(2.0)+np.square(3.5))
        hsv1[...,2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
        hsv1[...,0] = np.uint8(60)
        self.assertTrue(np.array_equal(hsv1, hsv_from_flow(flow)))

    def test_split_flow_components(self):
        flow = np.zeros((16,9,2), np.float32)
        flow[...,0] = 1.0
        flow[...,1] = 2.0
        u,v = split_flow_components(flow)
        self.assertTrue(np.array_equal(u, flow[...,0]))
        self.assertTrue(np.array_equal(v, flow[...,1]))

    def test_merge_flow_components(self):
        u = np.zeros((16,9), np.float32)
        v = np.zeros((16,9), np.float32)
        u[...] = 1.0
        v[...] = 2.0
        flow1 = merge_flow_components(u,v)
        flow2 = np.zeros((16,9,2), np.float32)
        flow2[...,0] = 1.0
        flow2[...,1] = 2.0
        self.assertTrue(np.array_equal(flow1, flow2))


if __name__ == '__main__':
    unittest.main()
