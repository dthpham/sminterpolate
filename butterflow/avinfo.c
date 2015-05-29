#include <Python.h>
#include <stdio.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/mathematics.h>

#define MIN(A,B) (((A)<(B))?(A):(B))
#define MAX(A,B) (((A)>(B))?(A):(B))
#define py_safe_set(A, B, C) if((PyDict_SetItemString((A), (B), (C))) != 0) { \
    PyErr_SetString(PyExc_RuntimeError, "set dict failed"); \
    return (PyObject*)NULL; }
#define MS_PER_SEC 1000


static PyObject*
get_info(PyObject *self, PyObject *arg) {
    char *vid_path = PyString_AsString(arg);

    av_register_all();

    AVFormatContext *format_ctx = avformat_alloc_context();

    int ret = avformat_open_input(&format_ctx, vid_path, NULL, NULL);
    if (ret != 0) {
        PyErr_SetString(PyExc_RuntimeError, "could not open input");
        return (PyObject*)NULL;
    }
    ret = avformat_find_stream_info(format_ctx, NULL);
    if (ret < 0) {
        avformat_close_input(&format_ctx);
        PyErr_SetString(PyExc_RuntimeError, "could not find stream");
        return (PyObject*)NULL;
    }

    int v_stream_idx = av_find_best_stream(format_ctx, AVMEDIA_TYPE_VIDEO,
                                           -1, -1, NULL, 0);
    int a_stream_idx = av_find_best_stream(format_ctx, AVMEDIA_TYPE_AUDIO,
                                           -1, -1, NULL, 0);
    int s_stream_idx = av_find_best_stream(format_ctx, AVMEDIA_TYPE_SUBTITLE,
                                           -1, -1, NULL, 0);

    int v_stream_exists = 1;
    int a_stream_exists = 1;
    int s_stream_exists = 1;

    if (v_stream_idx == AVERROR_STREAM_NOT_FOUND ||
        v_stream_idx == AVERROR_DECODER_NOT_FOUND) {
        v_stream_exists = 0;
    }
    if (a_stream_idx == AVERROR_STREAM_NOT_FOUND ||
        a_stream_idx == AVERROR_DECODER_NOT_FOUND) {
        a_stream_exists = 0;
    }
    if (s_stream_idx == AVERROR_STREAM_NOT_FOUND ||
        s_stream_idx == AVERROR_DECODER_NOT_FOUND) {
        s_stream_exists = 0;
    }

    int w = 0;
    int h = 0;
    int64_t duration = 0.0;
    int64_t v_duration = 0.0;
    int64_t c_duration = 0.0;
    int rate_num = -1;
    int rate_den = -1;
    double min_rate = 0.0;
    unsigned long frames = 0;

    if (v_stream_exists) {
        AVStream *v_stream = format_ctx->streams[v_stream_idx];

        AVRational ms_tb = {1, MS_PER_SEC};
        AVRational av_tb = {1, AV_TIME_BASE};

        v_duration = av_rescale_q(v_stream->duration, v_stream->time_base,
                                  ms_tb);
        c_duration = av_rescale_q(format_ctx->duration, av_tb, ms_tb);

        duration = MAX(v_duration, c_duration);

        AVCodecContext *v_codec_ctx = format_ctx->streams[v_stream_idx]->codec;

        w = v_codec_ctx->width;
        h = v_codec_ctx->height;

        AVRational rational_rate =
            format_ctx->streams[v_stream_idx]->avg_frame_rate;

        rate_num = rational_rate.num;
        rate_den = rational_rate.den;
        double rate = rate_num * 1.0 / rate_den;

        frames = rate * (duration / 1000.0);
        // min_rate is the smallest possible rate of the video stream that can
        // be represented without losing any unique frames
        min_rate   = frames / (duration / 1000.0);
    }

    // An avformat_free_context call is not needed because avformat_close_input
    // will automatically perform file cleanup and free everything associated
    // with the file. Calling free after close will trigger a segfault for for
    // those using Libav
    avformat_close_input(&format_ctx);

    PyObject *py_info = PyDict_New();

    py_safe_set(py_info, "path", PyString_FromString(vid_path));
    py_safe_set(py_info, "v_stream_exists", PyBool_FromLong(v_stream_exists));
    py_safe_set(py_info, "a_stream_exists", PyBool_FromLong(a_stream_exists));
    py_safe_set(py_info, "s_stream_exists", PyBool_FromLong(s_stream_exists));
    py_safe_set(py_info, "width", PyInt_FromLong(w));
    py_safe_set(py_info, "height", PyInt_FromLong(h));
    py_safe_set(py_info, "duration", PyFloat_FromDouble(duration));
    py_safe_set(py_info, "rate_num", PyInt_FromLong(rate_num));
    py_safe_set(py_info, "rate_den", PyInt_FromLong(rate_den));
    py_safe_set(py_info, "min_rate", PyFloat_FromDouble(min_rate));
    py_safe_set(py_info, "frames", PyInt_FromLong(frames));

    return py_info;
}

static PyMethodDef ModuleMethods[] = {
    {"get_info", get_info, METH_O, ""},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initavinfo(void) {
    (void)Py_InitModule("avinfo", ModuleMethods);
}
