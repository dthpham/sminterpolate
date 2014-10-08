#ifndef PY_MOTION_H
#define PY_MOTION_H
#include <Python.h>

static PyObject*
py_ocl_device_available(PyObject *self, PyObject *noargs);
static PyObject*
py_print_ocl_devices(PyObject *self, PyObject *noargs);
static PyObject*
py_ocl_set_cache_path(PyObject *self, PyObject *arg);
static PyObject*
py_ocl_interpolate_flow(PyObject *self, PyObject *args);
static PyObject*
py_ocl_farneback_optical_flow(PyObject *self, PyObject *args);

#endif
