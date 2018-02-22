#include "opencv-ndarray-conversion/conversion.h"
/*
 * The following conversion functions are taken/adapted from OpenCV's cv2.cpp
 * file inside modules/python/src2 folder.
 */

static void init()
{
    import_array();
}

static int failmsg(const char *fmt, ...)
{
    char str[1000];

    va_list ap;
    va_start(ap, fmt);
    vsnprintf(str, sizeof(str), fmt, ap);
    va_end(ap);

    PyErr_SetString(PyExc_TypeError, str);
    return 0;
}

class PyAllowThreads
{
public:
    PyAllowThreads() : _state(PyEval_SaveThread()) {}
    ~PyAllowThreads()
    {
        PyEval_RestoreThread(_state);
    }
private:
    PyThreadState* _state;
};

class PyEnsureGIL
{
public:
    PyEnsureGIL() : _state(PyGILState_Ensure()) {}
    ~PyEnsureGIL()
    {
        PyGILState_Release(_state);
    }
private:
    PyGILState_STATE _state;
};

using namespace cv;

class NumpyAllocator : public MatAllocator
{
public:
    NumpyAllocator() {}
    ~NumpyAllocator() {}

    void allocate(int dims, const int* sizes, int type, int*& refcount,
                  uchar*& datastart, uchar*& data, size_t* step)
    {
        PyEnsureGIL gil;

        int depth = CV_MAT_DEPTH(type);
        int cn = CV_MAT_CN(type);
        const int f = (int)(sizeof(size_t)/8);
        int typenum = depth == CV_8U ? NPY_UBYTE : depth == CV_8S ? NPY_BYTE :
                      depth == CV_16U ? NPY_USHORT : depth == CV_16S ? NPY_SHORT :
                      depth == CV_32S ? NPY_INT : depth == CV_32F ? NPY_FLOAT :
                      depth == CV_64F ? NPY_DOUBLE : f*NPY_ULONGLONG + (f^1)*NPY_UINT;
        int i;
        npy_intp _sizes[CV_MAX_DIM+1];
        for( i = 0; i < dims; i++ )
        {
            _sizes[i] = sizes[i];
        }

        if( cn > 1 )
        {
            _sizes[dims++] = cn;
        }

        PyObject* o = PyArray_SimpleNew(dims, _sizes, typenum);

        if(!o)
        {
            CV_Error_(CV_StsError, ("The numpy array of typenum=%d, ndims=%d can not be created", typenum, dims));
        }
        refcount = refcountFromPyObject(o);

        npy_intp* _strides = PyArray_STRIDES(o);
        for( i = 0; i < dims - (cn > 1); i++ )
            step[i] = (size_t)_strides[i];
        datastart = data = (uchar*)PyArray_DATA(o);
    }

    void deallocate(int* refcount, uchar*, uchar*)
    {
        PyEnsureGIL gil;
        if( !refcount )
            return;
        PyObject* o = pyObjectFromRefcount(refcount);
        Py_INCREF(o);
        Py_DECREF(o);
    }
};

NumpyAllocator g_numpyAllocator;

NDArrayConverter::NDArrayConverter() { init(); }

void NDArrayConverter::init()
{
    import_array();
}

cv::Mat NDArrayConverter::toMat(const PyObject *o)
{
    cv::Mat m;

    if(!o || o == Py_None)
    {
        if( !m.data )
            m.allocator = &g_numpyAllocator;
        return m;
    }

    if( PyInt_Check(o) )
    {
        double v[] = {static_cast<double>(PyInt_AsLong((PyObject*)o)), 0., 0., 0.};
        m = Mat(4, 1, CV_64F, v).clone();
        return m;
    }
    if( PyFloat_Check(o) )
    {
        double v[] = {PyFloat_AsDouble((PyObject*)o), 0., 0., 0.};
        m = Mat(4, 1, CV_64F, v).clone();
        return m;
    }
    if( PyTuple_Check(o) )
    {
        int i, sz = (int)PyTuple_Size((PyObject*)o);
        m = Mat(sz, 1, CV_64F);
        for( i = 0; i < sz; i++ )
        {
            PyObject* oi = PyTuple_GET_ITEM(o, i);
            if( PyInt_Check(oi) )
                m.at<double>(i) = (double)PyInt_AsLong(oi);
            else if( PyFloat_Check(oi) )
                m.at<double>(i) = (double)PyFloat_AsDouble(oi);
            else
            {
                failmsg("array is not a numerical tuple");
                m.release();
                return m;
            }
        }
        return m;
    }

    if( !PyArray_Check(o) )
    {
        failmsg("array is not a numpy array, neither a scalar");
        return m;
    }

    PyArrayObject* oarr = (PyArrayObject*) o;

    bool needcopy = false, needcast = false;
    int typenum = PyArray_TYPE(oarr), new_typenum = typenum;
    int type = typenum == NPY_UBYTE ? CV_8U :
               typenum == NPY_BYTE ? CV_8S :
               typenum == NPY_USHORT ? CV_16U :
               typenum == NPY_SHORT ? CV_16S :
               typenum == NPY_INT ? CV_32S :
               typenum == NPY_INT32 ? CV_32S :
               typenum == NPY_FLOAT ? CV_32F :
               typenum == NPY_DOUBLE ? CV_64F : -1;

    if( type < 0 )
    {
        if( typenum == NPY_INT64 || typenum == NPY_UINT64 || type == NPY_LONG )
        {
            needcopy = needcast = true;
            new_typenum = NPY_INT;
            type = CV_32S;
        }
        else
        {
            failmsg("data type = %d is not supported", typenum);
            return m;
        }
    }

    int ndims = PyArray_NDIM(oarr);
    if(ndims >= CV_MAX_DIM)
    {
        failmsg("dimensionality (=%d) is too high", ndims);
        return m;
    }

    int size[CV_MAX_DIM+1];
    size_t step[CV_MAX_DIM+1], elemsize = CV_ELEM_SIZE1(type);
    const npy_intp* _sizes = PyArray_DIMS(oarr);
    const npy_intp* _strides = PyArray_STRIDES(oarr);
    bool ismultichannel = ndims == 3 && _sizes[2] <= CV_CN_MAX;

    for( int i = ndims-1; i >= 0 && !needcopy; i-- )
    {
        // these checks handle cases of
        //  a) multi-dimensional (ndims > 2) arrays, as well as simpler 1- and 2-dimensional cases
        //  b) transposed arrays, where _strides[] elements go in non-descending order
        //  c) flipped arrays, where some of _strides[] elements are negative
        if( (i == ndims-1 && (size_t)_strides[i] != elemsize) ||
            (i < ndims-1 && _strides[i] < _strides[i+1]) )
            needcopy = true;
    }

    if( ismultichannel && _strides[1] != (npy_intp)elemsize*_sizes[2] )
        needcopy = true;

    if (needcopy)
    {

        if( needcast ) {
            o = PyArray_Cast(oarr, new_typenum);
            oarr = (PyArrayObject*) o;
        }
        else {
            oarr = PyArray_GETCONTIGUOUS(oarr);
            o = (PyObject*) oarr;
        }

        _strides = PyArray_STRIDES(oarr);
    }

    for(int i = 0; i < ndims; i++)
    {
        size[i] = (int)_sizes[i];
        step[i] = (size_t)_strides[i];
    }

    // handle degenerate case
    if( ndims == 0) {
        size[ndims] = 1;
        step[ndims] = elemsize;
        ndims++;
    }

    if( ismultichannel )
    {
        ndims--;
        type |= CV_MAKETYPE(0, size[2]);
    }

    if( ndims > 2 )
    {
        failmsg("has more than 2 dimensions");
        return m;
    }

    m = Mat(ndims, size, type, PyArray_DATA(oarr), step);

    if( m.data )
    {
        m.refcount = refcountFromPyObject(o);
        if (!needcopy)
        {
            m.addref(); // protect the original numpy array from deallocation
                        // (since Mat destructor will decrement the reference counter)
        }
    };
    m.allocator = &g_numpyAllocator;

    return m;
}

PyObject* NDArrayConverter::toNDArray(const cv::Mat& m)
{
    if( !m.data )
        Py_RETURN_NONE;
    Mat temp, *p = (Mat*)&m;
    if(!p->refcount || p->allocator != &g_numpyAllocator)
    {
        temp.allocator = &g_numpyAllocator;
        m.copyTo(temp);
        p = &temp;
    }
    p->addref();
    return pyObjectFromRefcount(p->refcount);
}
