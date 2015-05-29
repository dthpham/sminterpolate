import cv2
import numpy as np


def hsv_from_flow(flow):
    """creates a hue, saturation, value model of a flow"""
    r, c = flow.shape[:2]
    hsv = np.zeros((r, c, 3), np.uint8)
    mag, ang = cv2.cartToPolar(flow[...,0], flow[...,1], None, None, True)
    hsv[...,0] = ang + 0.5
    hsv[...,1] = 255
    hsv[...,2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    return hsv


def bgr_from_flow(fu, fv, bu, bv):
    """create bgr rendition of forward and backward flows given flow
    components"""
    f_flow = merge_flow_components(fu, fv)
    b_flow = merge_flow_components(bu, bv)
    f_bgr = cv2.cvtColor(hsv_from_flow(f_flow), cv2.COLOR_HSV2BGR)
    b_bgr = cv2.cvtColor(hsv_from_flow(b_flow), cv2.COLOR_HSV2BGR)
    return f_bgr, b_bgr


def split_flow_components(flow):
    """splits flow into separate horizontal and vertical components."""
    u = flow[:,:,0]
    v = flow[:,:,1]
    return u, v


def merge_flow_components(u, v):
    """merge flow components into a single flow, a 3dim object with the
    horizontal component in the first channel and the vertical component in the
    second."""
    r, c = u.shape[:2]
    flow = np.zeros((r, c, 2), u.dtype)
    flow[...,0] = u
    flow[...,1] = v
    return flow
