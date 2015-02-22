import cv2
import numpy as np
import py_motion


class Flow(object):
  '''collection of functions that handle and compute optical flows.
  flow are represented as numpy.ndarrays of type np.float32 with 3
  dimensions and 2 channels, one each for the `u` horizontal and `v`
  vertical components. each component defines the displacement at every
  point in an image.
  '''
  @staticmethod
  def hsv_from_flow(flow):
    '''creates a hue, saturation, value model of a flow, which can be
    converted to a bgr image to be displayed on the screen
    '''
    r, c = flow.shape[:2]
    hsv = np.zeros((r, c, 3), np.uint8)
    mag, ang = cv2.cartToPolar(flow[...,0], flow[...,1], None, None, True)
    hsv[...,0] = ang + 0.5
    hsv[...,1] = 255
    hsv[...,2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    return hsv

  @staticmethod
  def split_flow_components(flow):
    '''split flow into seperate horizontal and vertical components.'''
    u = flow[:,:,0]
    v = flow[:,:,1]
    return u, v

  @staticmethod
  def merge_flow_components(u, v):
    '''merges flow components into a single flow, a 3dim object with
    the horizontal component in the first and vertical component in
    the second channel
    '''
    r, c = u.shape[:2]
    flow = np.zeros((r, c, 2), u.dtype)
    flow[...,0] = u
    flow[...,1] = v
    return flow

  @staticmethod
  def farneback_optical_flow(fr_1, fr_2, scale, levels, winsize, iters, poly_n,
                             poly_sigma, flags):
    '''computes a dense optical flow using Gunnar Farneback's algorithm
    on the cpu. fr_1 and fr_2 should be grayscale images
    '''
    flow = cv2.calcOpticalFlowFarneback(
        fr_1, fr_2, scale, levels, winsize, iters, poly_n, poly_sigma, flags)
    u, v = Flow.split_flow_components(flow)
    return u, v

  @staticmethod
  def farneback_optical_flow_ocl(fr_1, fr_2, scale, levels, winsize, iters,
                                 poly_n, poly_sigma, flags):
    '''computes a dense optical flow using Gunnar Farneback's algorithm
    on a gpu using the opencl framework, if available
    '''
    flow = py_motion.py_ocl_farneback_optical_flow(
        fr_1, fr_2, scale, levels, winsize, iters, poly_n, poly_sigma, flags)
    u, v = flow
    return u, v

  @staticmethod
  def brox_optical_flow():
    '''computes a dense optical flow using the Brox algorithm'''
    pass

  @staticmethod
  def lucas_kanade_optical_flow():
    '''computes a sparse optical flow using the Lucas-Kanade method'''
    pass
