// Author: Duong Pham
// Copyright 2015

#include <Python.h>
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/ocl/ocl.hpp>
#include <opencv2/video/tracking.hpp>
#include "opencv-ndarray-conversion/conversion.h"

#define ocl_inter_frames(A, B, C, D) cv::ocl::interpolateFrames((A), (B), \
ocl_fu, ocl_fv, ocl_bu, ocl_bv, (D), (C), ocl_buf)

using namespace std;
using namespace cv;
using namespace cv::ocl;


static PyObject*
ocl_farneback_optical_flow(PyObject *self, PyObject *args) {
    PyObject *py_fr_1;
    PyObject *py_fr_2;

    PyObject *py_scale;
    PyObject *py_levels;
    PyObject *py_winsize;
    PyObject *py_iters;
    PyObject *py_poly_n;
    PyObject *py_poly_sigma;
    PyObject *py_fast_pyramids;
    PyObject *py_flags;

    if (!PyArg_UnpackTuple(args, "", 10, 10, &py_fr_1, &py_fr_2, &py_scale,
                           &py_levels, &py_winsize, &py_iters, &py_poly_n,
                           &py_poly_sigma, &py_fast_pyramids, &py_flags)) {
        PyErr_SetString(PyExc_TypeError, "could not unpack tuple");
        return (PyObject*)NULL;
    }

    double scale = PyFloat_AsDouble(py_scale);
    int levels   = PyInt_AsLong(py_levels);
    int winsize  = PyInt_AsLong(py_winsize);
    int iters    = PyInt_AsLong(py_iters);
    int poly_n   = PyInt_AsLong(py_poly_n);
    double poly_sigma  = PyFloat_AsDouble(py_poly_sigma);
    bool fast_pyramids = PyObject_IsTrue(py_fast_pyramids);
    int flags    = PyInt_AsLong(py_flags);

    NDArrayConverter converter;
    Mat fr_1 = converter.toMat(py_fr_1);
    Mat fr_2 = converter.toMat(py_fr_2);

    oclMat ocl_fr_1;
    oclMat ocl_fr_2;

    ocl_fr_1.upload(fr_1);
    ocl_fr_2.upload(fr_2);

    cv::ocl::FarnebackOpticalFlow calc_flow;
    calc_flow.pyrScale  = scale;
    calc_flow.numLevels = levels;
    calc_flow.winSize   = winsize;
    calc_flow.numIters  = iters;
    calc_flow.polyN     = poly_n;
    calc_flow.polySigma = poly_sigma;
    calc_flow.fastPyramids = fast_pyramids;
    calc_flow.flags     = flags;

    oclMat ocl_flow_x;
    oclMat ocl_flow_y;

    calc_flow(ocl_fr_1, ocl_fr_2, ocl_flow_x, ocl_flow_y);

    Mat mat_flow_x;
    Mat mat_flow_y;

    ocl_flow_x.download(mat_flow_x);
    ocl_flow_y.download(mat_flow_y);

    calc_flow.releaseMemory();

    PyObject *py_flows = PyList_New(2);

    PyObject *py_flow_1 = converter.toNDArray(mat_flow_x);
    PyObject *py_flow_2 = converter.toNDArray(mat_flow_y);

    /* PyList_SetItem will steal a reference to items that are added to
     * the list. In other words, it now assumes it owns that reference
     * and the user is no longer responsible for it. The item will be
     * referenced in the list but it's reference count will not be
     * increased. When the list is deleted, every element in the list
     * will be decrefed. */
    PyList_SetItem(py_flows, 0, py_flow_1);
    PyList_SetItem(py_flows, 1, py_flow_2);

    return py_flows;
}

static PyObject*
time_steps_for_int_frames(PyObject *self, PyObject *arg) {
    int n = PyInt_AsLong(arg);   /* number of int frames */
    int sub_divisions  = n + 1;  /* splits in region from 0,1 */
    PyObject *py_steps = PyList_New(n);

    for (int i = 0; i < n; i++) {
        double time_step = max(0.0, min(1.0,
                             (1.0 / sub_divisions) * (i + 1)));
        /* Py_BuildValue +1 refcnt that will be stolen by PyList_SetItem */
        PyList_SetItem(py_steps, i, Py_BuildValue("d", time_step));
    }

    return py_steps;
}

static PyObject*
ocl_interpolate_flow(PyObject *self, PyObject *args) {
    PyObject *py_fr_1;
    PyObject *py_fr_2;

    PyObject *py_fu;
    PyObject *py_fv;
    PyObject *py_bu;
    PyObject *py_bv;

    PyObject *py_int_each_go;

    if (!PyArg_UnpackTuple(args, "", 7, 7, &py_fr_1, &py_fr_2, &py_fu, &py_fv,
                           &py_bu, &py_bv, &py_int_each_go)) {
        PyErr_SetString(PyExc_TypeError, "could not unpack tuple");
        return (PyObject*)NULL;
    }

    int int_each_go = PyInt_AsLong(py_int_each_go);

    if (int_each_go == 0) {
      return PyList_New(0);
    }

    NDArrayConverter converter;
    Mat fr_1 = converter.toMat(py_fr_1);
    Mat fr_2 = converter.toMat(py_fr_2);
    Mat fu   = converter.toMat(py_fu);
    Mat fv   = converter.toMat(py_fv);
    Mat bu   = converter.toMat(py_bu);
    Mat bv   = converter.toMat(py_bv);

    oclMat fr_1_b, fr_1_g, fr_1_r;
    oclMat fr_2_b, fr_2_g, fr_2_r;

    Mat channels[3];

    split(fr_1, channels);
    fr_1_b.upload(channels[0]);
    fr_1_g.upload(channels[1]);
    fr_1_r.upload(channels[2]);

    split(fr_2, channels);
    fr_2_b.upload(channels[0]);
    fr_2_g.upload(channels[1]);
    fr_2_r.upload(channels[2]);

    oclMat ocl_fu;
    oclMat ocl_fv;
    oclMat ocl_bu;
    oclMat ocl_bv;

    ocl_fu.upload(fu);
    ocl_fv.upload(fv);
    ocl_bu.upload(bu);
    ocl_bv.upload(bv);

    oclMat ocl_buf;
    oclMat ocl_new_b, ocl_new_g, ocl_new_r;
    oclMat ocl_new_bgr;

    PyObject *py_frs = PyList_New(0);
    PyObject *py_time_steps = time_steps_for_int_frames(self, py_int_each_go);

    for (int i = 0; i < int_each_go; i++) {
        PyObject *py_ts = PyList_GetItem(py_time_steps,
                                        (Py_ssize_t)i); /* borrowed ref */
        double ts = PyFloat_AsDouble(py_ts);

        ocl_inter_frames(fr_1_b, fr_2_b, ocl_new_b, ts);
        ocl_inter_frames(fr_1_g, fr_2_g, ocl_new_g, ts);
        ocl_inter_frames(fr_1_r, fr_2_r, ocl_new_r, ts);

        oclMat channels[] = {ocl_new_b, ocl_new_g, ocl_new_r};
        merge(channels, 3, ocl_new_bgr);

        Mat mat_new_bgr;
        ocl_new_bgr.download(mat_new_bgr);
        mat_new_bgr.convertTo(mat_new_bgr, CV_8UC3, 255.0);

        PyObject *py_new_fr = converter.toNDArray(mat_new_bgr);
        /* PyList_Append will increment reference count. This behavior
         * differs from PyList_SetItem which doesn't */
        PyList_Append(py_frs, py_new_fr);
        Py_DECREF(py_new_fr);
    }

    Py_DECREF(py_time_steps);

    return py_frs;
}

static PyObject*
set_cache_path(PyObject *self, PyObject *arg) {
    char *cache_path = PyString_AsString(arg);
    setBinaryPath(cache_path);

    Py_RETURN_NONE;
}

static PyObject*
set_num_threads(PyObject *self, PyObject *arg) {
    int n_threads = PyInt_AsLong(arg);
    setNumThreads(n_threads);

    Py_RETURN_NONE;
}

static PyMethodDef module_methods[] = {
    {"ocl_interpolate_flow", ocl_interpolate_flow, METH_VARARGS,
        "Interpolate flow from frames"},
    {"ocl_farneback_optical_flow", ocl_farneback_optical_flow, METH_VARARGS,
        "Calc farneback optical flow"},
    {"time_steps_for_int_frames", time_steps_for_int_frames, METH_O,
        "Get time steps for interpolated frames"},
    {"set_cache_path", set_cache_path, METH_O,
        "Sets the path of OpenCL kernel binaries"},
    {"set_num_threads", set_num_threads, METH_O,
        "Set the number of threads for the next parallel region"},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initmotion(void) {
    (void) Py_InitModule("motion", module_methods);
}
