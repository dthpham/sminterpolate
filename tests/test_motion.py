import unittest
import os
import sys
import cv2
from cv2 import calcOpticalFlowFarneback as sw_farneback_optical_flow
import numpy as np
from butterflow.motion import ocl_farneback_optical_flow, \
    ocl_interpolate_flow, set_cache_path
from butterflow import settings

clb_dir = settings.default['clb_dir']
if not os.path.exists(clb_dir):
    os.makedirs(clb_dir)
set_cache_path(clb_dir + os.sep)
SDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                    'samples')


class OpticalFlowTestCase(unittest.TestCase):
    def setUp(self):
        img_1 = os.path.join(SDIR, 'img-640x360-1.png')
        img_2 = os.path.join(SDIR, 'img-640x360-2.png')
        fr_1 = cv2.imread(img_1)
        fr_2 = cv2.imread(img_2)
        self.fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
        self.fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)
        self.u, self.v = \
            ocl_farneback_optical_flow(
                self.fr_1_gr,self.fr_2_gr,0.5,3,15,3,7,1.5,False,0)
        sw_flow = \
            sw_farneback_optical_flow(
                self.fr_1_gr,self.fr_2_gr,0.5,3,15,3,7,1.5,False,0)
        # split flow into horizontal and vertical components
        self.sw_u = sw_flow[:,:,0]
        self.sw_v = sw_flow[:,:,1]

    def _test_optical_flow_form(self, u, v):
        '''test if returns a flow field in the right form, doesnt
        verify values
        '''
        self.assertIsInstance(u, np.ndarray)
        self.assertIsInstance(v, np.ndarray)
        self.assertEqual(u.dtype, v.dtype)
        self.assertEqual(u.shape, v.shape)
        self.assertEqual(u.dtype, np.float32)
        self.assertEqual(len(u.shape), 2)
        r,c = u.shape
        self.assertEqual(r, 360)
        self.assertEqual(c, 640)

    def test_ocl_farneback_optical_flow_form(self):
        self._test_optical_flow_form(self.u,self.v)

    def test_farneback_optical_flow_form(self):
        self._test_optical_flow_form(self.sw_u,self.sw_v)

    @unittest.skip('todo')
    def test_farneback_optical_flow_ocl_vs_sw(self):
        '''test if opencl and software versions return the same
        values
        '''
        self.assertTrue(np.array_equal(self.u, self.sw_u))
        self.assertTrue(np.array_equal(self.v, self.sw_v))

    def test_farneback_optical_flow_refcnt(self):
        # sys.getrefcnt is generally one higher than expected.
        # creating an object is +1 refcnt. passing the object to
        # sys.getrefcount creates a temporary reference as an
        # argument is another + 1 refcnt
        u,v = ocl_farneback_optical_flow(
            self.fr_1_gr,self.fr_2_gr,0.5,3,15,3,7,1.5,False,0)
        self.assertEqual(sys.getrefcount(u), 1+1)
        self.assertEqual(sys.getrefcount(v), 1+1)

    def test_farneback_optical_flow_hires(self):
        fr_1 = cv2.imread(os.path.join(SDIR,'img-1920x1080-1.png'))
        fr_2 = cv2.imread(os.path.join(SDIR,'img-1920x1080-2.png'))
        fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
        fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)
        self.assertIsNotNone(
            ocl_farneback_optical_flow(
                fr_1_gr,fr_2_gr,0.5,3,15,3,7,1.5,False,0))


class InterpolateFlowTestCase(unittest.TestCase):
    def setUp(self):
        img_1 = os.path.join(SDIR, 'img-640x360-1.png')
        img_2 = os.path.join(SDIR, 'img-640x360-2.png')
        fr_1 = cv2.imread(img_1)
        fr_2 = cv2.imread(img_2)
        fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
        fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)
        self.fu, self.fv = \
            ocl_farneback_optical_flow(fr_1_gr,fr_2_gr,0.5,3,15,3,7,1.5,False,0)
        self.bu, self.bv = \
            ocl_farneback_optical_flow(fr_1_gr,fr_2_gr,0.5,3,15,3,7,1.5,False,0)
        self.fr_1_32 = np.float32(fr_1)*1/255.0
        self.fr_2_32 = np.float32(fr_2)*1/255.0
        self.ocl_inter_method = lambda t: \
            ocl_interpolate_flow(
                self.fr_1_32,self.fr_2_32,self.fu,self.fv,self.bu,self.bv,t)

    def test_ocl_interpolate_flow_form(self):
        fr = self.ocl_inter_method(0.5)[0]
        self.assertIsInstance(fr, np.ndarray)
        self.assertEqual(fr.dtype, np.uint8)
        self.assertEqual(len(fr.shape),3)
        r,c,ch = fr.shape
        self.assertEqual(r, 360)
        self.assertEqual(c, 640)
        self.assertEqual(ch, 3)

    def test_ocl_interpolate_flow_count(self):
        self.assertEqual(len(self.ocl_inter_method(0.500)),1)
        self.assertEqual(len(self.ocl_inter_method(0.250)),4-1)
        self.assertEqual(len(self.ocl_inter_method(0.125)),8-1)
        self.assertEqual(len(self.ocl_inter_method(0.0625)),16-1)
        self.assertEqual(len(self.ocl_inter_method(0.333)),3)
        self.assertEqual(len(self.ocl_inter_method(0.334)),2)
        self.assertEqual(len(self.ocl_inter_method(1)),0)

    def test_ocl_interpolate_flow_return_zero(self):
        self.assertEqual(len(self.ocl_inter_method(1)),0)
        self.assertEqual(len(self.ocl_inter_method(0)),0)

    def test_ocl_interpolate_flow_hires(self):
        fr_1 = cv2.imread(os.path.join(SDIR, 'img-1920x1080-1.png'))
        fr_2 = cv2.imread(os.path.join(SDIR, 'img-1920x1080-2.png'))
        fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
        fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)
        fu,fv = ocl_farneback_optical_flow(
            fr_1_gr,fr_2_gr,0.5,3,15,3,7,1.5,False,0)
        bu,bv = ocl_farneback_optical_flow(
            fr_2_gr,fr_1_gr,0.5,3,15,3,7,1.5,False,0)
        fr_1_32 = np.float32(fr_1)*1/255.0
        fr_2_32 = np.float32(fr_2)*1/255.0
        self.assertIsNotNone(
            ocl_interpolate_flow(fr_1_32,fr_2_32,fu,fv,bu,bv,0.500))

    def test_ocl_interpolate_flow_refcnt(self):
        # sys.getrefcnt is generally one higher than expected
        frs = self.ocl_inter_method(0.500)
        self.assertEqual(sys.getrefcount(frs),1+1)
        self.assertEqual(sys.getrefcount(frs[0]),1+1)
        frs = self.ocl_inter_method(0.334)
        self.assertEqual(sys.getrefcount(frs),1+1)
        self.assertEqual(sys.getrefcount(frs[0]),1+1)
        self.assertEqual(sys.getrefcount(frs[1]),1+1)


if __name__ == '__main__':
    unittest.main()
