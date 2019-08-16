#include <Python.h>
#include <iostream>
#include <stdio.h>
#if defined(__APPLE__) && defined(__MACH__)
    #include <OpenCL/opencl.h>
#else
    #include <CL/cl.h>
#endif
#include <opencv2/core/core.hpp>
#include <opencv2/ocl/ocl.hpp>

#define cl_safe(A) if((A) != CL_SUCCESS) { \
    PyErr_SetString(PyExc_RuntimeError, "opencl call failed"); \
    return (PyObject*)NULL; }

#define MIN_CL_VER 1.2

#define MIN_WORK_GROUP_SIZE 256

#define MIN_FB_UPDATEMATRICES_WORK_ITEM_SIZE        {32,  8, 1}
#define MIN_FB_BOXFILTER5_WORK_ITEM_SIZE            {256, 1, 1}
#define MIN_FB_UPDATEFLOW_WORK_ITEM_SIZE            {32,  8, 1}
#define MIN_FB_GAUSSIANBLUR_WORK_ITEM_SIZE          {256, 1, 1}
#define MIN_FB_POLYNOMIALEXPANSION_WORK_ITEM_SIZE   {256, 1, 1}
#define MIN_FB_GAUSSIANBLUR5_WORK_ITEM_SIZE         {256, 1, 1}

/* max of each work item size columns*/
static const int MIN_FB_WORK_ITEM_SIZES[3] = {256, 8, 1};


static int ocl_device_is_compatible(char *d_vers, char *d_prof, char *p_prof,
  size_t d_max_work_group_size, size_t *d_max_work_item_sizes);
static PyObject* compat_ocl_device_available(PyObject *self, PyObject *noargs);

using namespace std;
using namespace cv::ocl;


static PyObject*
print_ocl_devices(PyObject *self, PyObject *noargs) {
    cl_platform_id platforms[32];
    cl_uint n_platforms;
    cl_device_id *devices;
    cl_uint n_devices;
    char p_name[1024];
    char p_vend[1024];
    char p_vers[1024];
    char p_prof[1024];
    char d_name[1024];
    char d_vers[1024];
    char d_dver[1024];
    char d_prof[1024];
    cl_uint d_vendor_id;
    size_t d_max_work_group_size;
    size_t d_max_work_item_sizes[3];
    int d_num = 0;

    const DeviceInfo& currentDevice = Context::getContext()->getDeviceInfo();
    cl_uint currentVendorId = (cl_uint)currentDevice.deviceVendorId;

    cl_safe(clGetPlatformIDs(32, platforms, &n_platforms));

    if (n_platforms <= 0) {
        printf("No OpenCL devices detected. Please check your OpenCL "
               "installation.\n");
        Py_RETURN_NONE;
    }

    printf("OpenCL devices:");

    for (int i = 0; i < n_platforms; i++) {
        cl_platform_id p = platforms[i];
        cl_safe(clGetPlatformInfo(platforms[i], CL_PLATFORM_PROFILE, 1024,
                                  p_prof, NULL));
        cl_safe(clGetPlatformInfo(p, CL_PLATFORM_NAME, 1024, p_name, NULL));
        cl_safe(clGetPlatformInfo(p, CL_PLATFORM_VENDOR,  1024, p_vend, NULL));
        cl_safe(clGetPlatformInfo(p, CL_PLATFORM_VERSION, 1024, p_vers, NULL));
        printf("\n  Platform          \t: %s"
               "\n  Platform Vendor   \t: %s"
               "\n  Platform Version  \t: %s", p_name, p_vend, p_vers);

        cl_safe(clGetDeviceIDs(platforms[i], CL_DEVICE_TYPE_ALL, 0, NULL,
                               &n_devices));

        devices = (cl_device_id*)calloc(sizeof(cl_device_id), n_devices);
        cl_safe(clGetDeviceIDs(platforms[i], CL_DEVICE_TYPE_ALL, n_devices,
                               devices, NULL));

        for (int j = 0; j < n_devices; j++) {
            cl_device_id d = devices[j];
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_PROFILE, 1024, d_prof, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_NAME, 1024, d_name, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_VENDOR_ID, sizeof(d_vendor_id), &d_vendor_id, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_VERSION, 1024, d_vers, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DRIVER_VERSION, 1024, d_dver, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_MAX_WORK_GROUP_SIZE,
                                    sizeof(d_max_work_group_size),
                                    &d_max_work_group_size, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_MAX_WORK_ITEM_SIZES,
                                    sizeof(d_max_work_item_sizes),
                                    &d_max_work_item_sizes, NULL));
            int compatible = ocl_device_is_compatible(d_vers,
                                                      d_prof,
                                                      p_prof,
                                  d_max_work_group_size, d_max_work_item_sizes);
            char const *compatible_string = "Yes";
            if (!compatible) {
                compatible_string = "No";
            }
            bool isCurrentDevice = ( (currentVendorId == d_vendor_id) &&
                                    !(strcmp(currentDevice.deviceName.c_str(), d_name)) );
            char const *selected_string = " ";
            if (isCurrentDevice) {
                selected_string = "*";
            }
            printf("\n%s  Device %d    \t\t: %s"
                   "\n      Vendor Id\t\t: 0x%lx"
                   "\n      Version  \t\t: %s"
                   "\n      Version  \t\t: %s"
                   "\n      Work Sizes\t: %lu, %lux%lux%lu"
                   "\n      Compatible\t: %s",
                   selected_string, d_num, d_name, d_vendor_id, d_vers, d_dver,
                   d_max_work_group_size,
                   d_max_work_item_sizes[0],
                   d_max_work_item_sizes[1],
                   d_max_work_item_sizes[2],
                   compatible_string);

           d_num++;
        }
        free(devices);
    }
    printf("\n");
    Py_RETURN_NONE;
}

static int
ocl_device_is_compatible(char *d_vers, char *d_prof, char *p_prof,
  size_t d_max_work_group_size, size_t *d_max_work_item_sizes) {
  int compatible = 1;
  char *cl_version_string = strtok(d_vers, "OpenCL ");

  compatible &= atof(cl_version_string) >= MIN_CL_VER;
  compatible &= strcmp(d_prof, "FULL_PROFILE") == 0;
  compatible &= strcmp(p_prof, "FULL_PROFILE") == 0;
  compatible &= d_max_work_group_size    >= MIN_WORK_GROUP_SIZE;
  compatible &= d_max_work_item_sizes[0] >= MIN_FB_WORK_ITEM_SIZES[0];
  compatible &= d_max_work_item_sizes[1] >= MIN_FB_WORK_ITEM_SIZES[1];
  compatible &= d_max_work_item_sizes[2] >= MIN_FB_WORK_ITEM_SIZES[2];

  return compatible;
}

static PyObject*
compat_ocl_device_available(PyObject *self, PyObject *noargs) {
    cl_platform_id platforms[32];
    cl_uint n_platforms;
    cl_device_id *devices;
    cl_uint n_devices;
    char p_prof[1024];
    char d_vers[1024];
    char d_prof[1024];
    size_t d_max_work_group_size;
    size_t d_max_work_item_sizes[3];

    cl_safe(clGetPlatformIDs(32, platforms, &n_platforms));

    for (int i = 0; i < n_platforms; i++) {
        cl_safe(clGetPlatformInfo(platforms[i], CL_PLATFORM_PROFILE, 1024,
                                  p_prof, NULL));

        cl_safe(clGetDeviceIDs(platforms[i], CL_DEVICE_TYPE_ALL, 0, NULL,
                               &n_devices));

        devices = (cl_device_id*)calloc(sizeof(cl_device_id), n_devices);
        cl_safe(clGetDeviceIDs(platforms[i], CL_DEVICE_TYPE_ALL, n_devices,
                               devices, NULL));

        for (int j = 0; j < n_devices; j++) {
            cl_device_id d = devices[j];

            cl_safe(clGetDeviceInfo(d, CL_DEVICE_VERSION, 1024, d_vers, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_PROFILE, 1024, d_prof, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_MAX_WORK_GROUP_SIZE,
                                    sizeof(d_max_work_group_size),
                                    &d_max_work_group_size, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_MAX_WORK_ITEM_SIZES,
                                    sizeof(d_max_work_item_sizes),
                                    &d_max_work_item_sizes, NULL));

            if (ocl_device_is_compatible(d_vers, d_prof, p_prof,
                                        d_max_work_group_size,
                                        d_max_work_item_sizes)) {
                free(devices);
                Py_RETURN_TRUE;
            }
        }
        free(devices);
    }
    Py_RETURN_FALSE;
}

static PyObject*
select_ocl_device(PyObject *self, PyObject *arg) {
    int preferred_device_num = PyInt_AsLong(arg);
    int current_device_num = 0;

    cl_platform_id platforms[32];
    cl_uint n_platforms;
    cl_device_id *devices;
    cl_uint n_devices;
    char p_prof[1024];
    char d_name[1024];
    char d_vers[1024];
    char d_prof[1024];
    size_t d_max_work_group_size;
    size_t d_max_work_item_sizes[3];

    cl_safe(clGetPlatformIDs(32, platforms, &n_platforms));

    for (int i = 0; i < n_platforms; i++) {
        cl_safe(clGetPlatformInfo(platforms[i], CL_PLATFORM_PROFILE, 1024,
                                  p_prof, NULL));

        cl_safe(clGetDeviceIDs(platforms[i], CL_DEVICE_TYPE_ALL, 0, NULL,
                               &n_devices));

        devices = (cl_device_id*)calloc(sizeof(cl_device_id), n_devices);
        cl_safe(clGetDeviceIDs(platforms[i], CL_DEVICE_TYPE_ALL, n_devices,
                               devices, NULL));

        for (int j = 0; j < n_devices; j++) {
            cl_device_id d = devices[j];

            cl_safe(clGetDeviceInfo(d, CL_DEVICE_NAME, 1024, d_name, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_VERSION, 1024, d_vers, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_PROFILE, 1024, d_prof, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_MAX_WORK_GROUP_SIZE,
                                    sizeof(d_max_work_group_size),
                                    &d_max_work_group_size, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_MAX_WORK_ITEM_SIZES,
                                    sizeof(d_max_work_item_sizes),
                                    &d_max_work_item_sizes, NULL));

            if (current_device_num == preferred_device_num) {
                bool found_device = false;
                DevicesInfo devicesInfo;
                getOpenCLDevices(devicesInfo, CVCL_DEVICE_TYPE_ALL, NULL);
                for(vector<const DeviceInfo*>::iterator it = devicesInfo.begin(); it != devicesInfo.end(); ++it) {
                    const DeviceInfo *deviceInfo = *it;

                    if ( !(strcmp(deviceInfo->deviceName.c_str(), d_name)) ) {
                        setDevice(deviceInfo);
                        found_device = true;
                        break;
                    }
                }
                free(devices);
                if (!found_device) {
                    PyErr_SetString(PyExc_RuntimeError, "Couldn't set the device");
                    return (PyObject*)NULL;
                }
                if (ocl_device_is_compatible(d_vers, d_prof, p_prof,
                                             d_max_work_group_size,
                                             d_max_work_item_sizes)) {
                    Py_RETURN_TRUE;
                } else {
                    PyErr_SetString(PyExc_ValueError, "Selected an incompatible device");
                    return (PyObject*)NULL;
                }
            }
            current_device_num++;
        }
        free(devices);
    }
    PyErr_SetString(PyExc_IndexError, "Invalid device number");
    return (PyObject*)NULL;
}

static PyObject*
set_cache_path(PyObject *self, PyObject *arg) {
    char *cache_path = PyString_AsString(arg);
    cv::ocl::setBinaryPath(cache_path);

    Py_RETURN_NONE;
}

static PyObject*
set_num_threads(PyObject *self, PyObject *arg) {
    int n_threads = PyInt_AsLong(arg);
    cv::setNumThreads(n_threads);

    Py_RETURN_NONE;
}

static PyObject*
get_current_ocl_device_name(PyObject *self, PyObject *noargs) {
    const DeviceInfo& currentDevice = Context::getContext()->getDeviceInfo();
    return PyString_FromString(currentDevice.deviceName.c_str());
}

static PyMethodDef module_methods[] = {
    {"compat_ocl_device_available", compat_ocl_device_available, METH_NOARGS,
        "Checks if a compatible ocl device is available"},
    {"print_ocl_devices", print_ocl_devices, METH_NOARGS,
        "Prints all available OpenCL devices"},
    {"get_current_ocl_device_name", get_current_ocl_device_name, METH_NOARGS,
        "Returns current OpenCL device name"},
    {"select_ocl_device", select_ocl_device, METH_O,
        "Set the preferred OpenCL device"},
    {"set_cache_path", set_cache_path, METH_O,
        "Sets the path of OpenCL kernel binaries"},
    {"set_num_threads", set_num_threads, METH_O,
        "Set the number of threads for the next parallel region"},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initocl(void) {
    (void) Py_InitModule("ocl", module_methods);
}
