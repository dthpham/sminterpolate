// get info on the opencl environment

#include <Python.h>
#include <stdio.h>
#if defined(__APPLE__) && defined(__MACH__)
    #include <OpenCL/opencl.h>
#else
    #include <CL/cl.h>
#endif

#define cl_safe(A) if((A) != CL_SUCCESS) { \
    PyErr_SetString(PyExc_RuntimeError, "opencl call failed"); \
    return (PyObject*)NULL; }
#define MIN_CL_VER 1.2


static PyObject*
print_ocl_devices(PyObject *self, PyObject *noargs) {
    cl_platform_id platforms[32];
    cl_uint n_platforms;
    cl_device_id *devices;
    cl_uint n_devices;
    char p_name[1024];
    char p_vend[1024];
    char p_vers[1024];
    char d_name[1024];
    char d_vers[1024];
    char d_dver[1024];

    cl_safe(clGetPlatformIDs(32, platforms, &n_platforms));

    if (n_platforms <= 0) {
        printf("No OpenCL devices detected. Please check your OpenCL "
               "installation.\n");
        Py_RETURN_NONE;
    }

    printf("OpenCL devices:");

    for (int i = 0; i < n_platforms; i++) {
        cl_platform_id p = platforms[i];
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
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_NAME, 1024, d_name, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_VERSION, 1024, d_vers, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DRIVER_VERSION, 1024, d_dver, NULL));
            printf("\n    Device    \t\t: %s"
                   "\n      Version \t\t: %s"
                   "\n      Version \t\t: %s", d_name, d_vers, d_dver);
        }
        free(devices);
    }
    printf("\n");
    Py_RETURN_NONE;
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
            int compatible = 1;
            cl_device_id d = devices[j];

            cl_safe(clGetDeviceInfo(d, CL_DEVICE_VERSION, 1024, d_vers, NULL));
            cl_safe(clGetDeviceInfo(d, CL_DEVICE_PROFILE, 1024, d_prof, NULL));

            char *p = strtok(d_vers, "OpenCL ");
            float cl_version = atof(p);

            compatible &= cl_version >= MIN_CL_VER;
            compatible &= strcmp(d_prof, "FULL_PROFILE") == 0;
            compatible &= strcmp(p_prof, "FULL_PROFILE") == 0;

            if (compatible) {
                free(devices);
                Py_RETURN_TRUE;
            }
        }
        free(devices);
    }
    Py_RETURN_FALSE;
}

static PyMethodDef module_methods[] = {
    {"compat_ocl_device_available", compat_ocl_device_available, METH_NOARGS,
        "Checks if a compatible ocl device is available"},
    {"print_ocl_devices", print_ocl_devices, METH_NOARGS,
        "Prints all available OpenCL devices"},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initocl(void) {
    (void) Py_InitModule("ocl", module_methods);
}
