#include <Python.h>
#include <stdio.h>
#include <iostream>
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include "ocl_interpolate.h"
#include "ocl_optical_flow.h"
#include "conversion.h"
#include <opencv2/ocl/ocl.hpp>
#include <CL/cl.hpp>

using namespace std;
using namespace cv;
using namespace cv::ocl;


static PyObject*
py_ocl_set_cache_path(PyObject *self, PyObject *arg) {
  char *cache_path = PyString_AsString(arg);
  setBinaryPath(cache_path);
  return PyBool_FromLong(1);
}

static void
print_ocl_devices() {
  vector<cl::Platform> all_platforms;
  cl::Platform::get(&all_platforms);

  if (all_platforms.size() > 0) {
    cout << "opencl devices:";
  }

  for (int i = 0; i < all_platforms.size(); i++) {
    cl::Platform platform = all_platforms[i];
    cout << "\n  Platform          \t: " << platform.getInfo<CL_PLATFORM_NAME>()
         << "\n  Platform Vendor   \t: " << platform.getInfo<CL_PLATFORM_VENDOR>()
         << "\n  Platform Version  \t: " << platform.getInfo<CL_PLATFORM_VERSION>();

    vector<cl::Device> all_devices;
    all_platforms[i].getDevices(CL_DEVICE_TYPE_ALL, &all_devices);
    for (int j = 0; j < all_devices.size(); j++) {
      cl::Device device = all_devices[j];
      cout << "\n    Device    \t\t: " << device.getInfo<CL_DEVICE_NAME>()
           << "\n      Version \t\t: " << device.getInfo<CL_DEVICE_VERSION>()
           << "\n      Driver  \t\t: " << device.getInfo<CL_DRIVER_VERSION>();
    }
  }
  cout << endl;
}

static PyObject*
py_print_ocl_devices(PyObject *self, PyObject *noargs) {
  print_ocl_devices();
  Py_RETURN_NONE;
}

static int
ocl_device_available() {
  int n_compat_devices = 0;
  vector<cl::Platform> all_platforms;
  cl::Platform::get(&all_platforms);

  for (int i = 0; i < all_platforms.size(); i++) {
    cl::Platform platform = all_platforms[i];
    vector<cl::Device> all_devices;
    all_platforms[i].getDevices(CL_DEVICE_TYPE_ALL, &all_devices);

    for (int j = 0; j < all_devices.size(); j++) {
      cl::Device device = all_devices[j];
      n_compat_devices++;
    }
  }
  return n_compat_devices > 0;
}

static PyObject*
py_ocl_device_available(PyObject *self, PyObject *noargs) {
  return PyBool_FromLong(ocl_device_available());
}

static void
mat_vector_fill_pylist(vector<Mat>& mats, PyObject* py_list) {
  NDArrayConverter converter;
  vector<Mat>::iterator it;

  for (it = mats.begin(); it != mats.end(); ++it) {
    int idx = it - mats.begin();
    PyObject *obj = converter.toNDArray(*it);
    PyList_SetItem(py_list, idx, obj);
  }
}

static PyObject*
py_ocl_farneback_optical_flow(PyObject *self, PyObject *args) {
  PyObject *py_fr_1;
  PyObject *py_fr_2;

  PyObject *py_scale;
  PyObject *py_levels;
  PyObject *py_winsize;
  PyObject *py_iters;
  PyObject *py_poly_n;
  PyObject *py_poly_sigma;
  PyObject *py_flags;

  if (!PyArg_UnpackTuple(args, "", 9, 9, &py_fr_1,
      &py_fr_2, &py_scale, &py_levels, &py_winsize, &py_iters, &py_poly_n,
      &py_poly_sigma, &py_flags)) {
    printf("Error unpacking tuple\n");
    Py_RETURN_NONE;
  }

  double scale  = PyFloat_AsDouble(py_scale);
  int levels    = PyInt_AsLong(py_levels);
  int winsize   = PyInt_AsLong(py_winsize);
  int iters     = PyInt_AsLong(py_iters);
  int poly_n    = PyInt_AsLong(py_poly_n);
  double poly_sigma = PyFloat_AsDouble(py_poly_sigma);
  int flags     = PyInt_AsLong(py_flags);

  NDArrayConverter converter;
  Mat fr_1 = converter.toMat(py_fr_1);
  Mat fr_2 = converter.toMat(py_fr_2);

  vector<Mat> flows = ocl_farneback_optical_flow(fr_1, fr_2, scale, levels,
      winsize, iters, poly_n, poly_sigma, flags);
  PyObject *py_flows = PyList_New(flows.size());

  mat_vector_fill_pylist(flows, py_flows);
  return py_flows;
}

static PyObject*
py_ocl_interpolate_flow(PyObject *self, PyObject *args) {
  PyObject *py_fr_1;
  PyObject *py_fr_2;

  PyObject *py_fu;
  PyObject *py_fv;
  PyObject *py_bu;
  PyObject *py_bv;

  PyObject *py_time_step;

  if (!PyArg_UnpackTuple(args, "", 7, 7, &py_fr_1, &py_fr_2, &py_fu, &py_fv,
        &py_bu, &py_bv, &py_time_step)) {
    printf("Error unpacking tuple\n");
    Py_RETURN_NONE;
  }

  float time_step = PyFloat_AsDouble(py_time_step);

  NDArrayConverter converter;
  Mat fr_1  = converter.toMat(py_fr_1);
  Mat fr_2  = converter.toMat(py_fr_2);
  Mat fu    = converter.toMat(py_fu);
  Mat fv    = converter.toMat(py_fv);
  Mat bu    = converter.toMat(py_bu);
  Mat bv    = converter.toMat(py_bv);

  vector<Mat> frs  = ocl_interpolate_flow(fr_1, fr_2, fu, fv, bu, bv, time_step);
  PyObject *py_frs = PyList_New(frs.size());

  mat_vector_fill_pylist(frs, py_frs);
  return py_frs;
}

static PyObject*
py_interpolate_flow(PyObject *self, PyObject *args) {
  Py_RETURN_NONE;
}

static PyMethodDef module_methods[] = {
  {"py_ocl_interpolate_flow", py_ocl_interpolate_flow, METH_VARARGS,
      "Interpolate flow from frames"},
  {"py_ocl_farneback_optical_flow", py_ocl_farneback_optical_flow, METH_VARARGS,
      "Calc farneback optical flow"},
  {"py_ocl_device_available", py_ocl_device_available, METH_NOARGS,
      "Checks if an ocl device is available"},
  {"py_print_ocl_devices", py_print_ocl_devices, METH_NOARGS,
      "Prints all available OpenCL devices"},
  {"py_ocl_set_cache_path", py_ocl_set_cache_path, METH_O,
      "Sets the path of OpenCL kernel binaries"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initpy_motion(void) {
  (void) Py_InitModule("py_motion", module_methods);
}
