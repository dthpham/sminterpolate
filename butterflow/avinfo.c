// get av file info

#include <Python.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
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
#define EPSILON 1.0e-8


int gcd(int a, int b) {
    return b == 0 ? a : gcd(b, a % b);
}

int almost_equal(double a, double b) {
    return fabs(a - b) <= EPSILON;
}

static PyObject*
get_av_info(PyObject *self, PyObject *arg) {
    char *path = PyString_AsString(arg);
    PyObject *py_info;

    av_register_all();

    AVFormatContext *format_ctx = avformat_alloc_context();

    int initial_level = av_log_get_level();
    av_log_set_level(AV_LOG_ERROR);  /* make quiet */

    int rc = avformat_open_input(&format_ctx, path, NULL, NULL);
    if (rc != 0) {
        PyErr_SetString(PyExc_RuntimeError, "open input failed");
        return (PyObject*)NULL;
    }

    rc = avformat_find_stream_info(format_ctx, NULL);
    if (rc < 0) {
        avformat_close_input(&format_ctx);
        PyErr_SetString(PyExc_RuntimeError, "no stream info found");
        return (PyObject*)NULL;
    }

    int v_stream_idx = av_find_best_stream(format_ctx, AVMEDIA_TYPE_VIDEO,
                                           -1, -1, NULL, 0);
    int a_stream_idx = av_find_best_stream(format_ctx, AVMEDIA_TYPE_AUDIO,
                                           -1, -1, NULL, 0);
    int s_stream_idx = av_find_best_stream(format_ctx, AVMEDIA_TYPE_SUBTITLE,
                                           -1, -1, NULL, 0);

    /* check if streams exist and can be decoded */
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
    int64_t duration = 0.0;    /* in milliseconds */
    unsigned long frames = 0;
    AVRational sar  = {0, 0};  /* sample aspect ratio */
    AVRational dar  = {0, 0};  /* display aspect ratio */
    float rate = 0.0;          /* average fps */
    AVRational rational_rate = {0, 0};

    if (v_stream_exists) {
        AVStream *v_stream = format_ctx->streams[v_stream_idx];

        AVRational ms_tb = {1, MS_PER_SEC};
        AVRational av_tb = {1, AV_TIME_BASE};

        int64_t v_duration = av_rescale_q(v_stream->duration,
                                          v_stream->time_base, ms_tb);
        int64_t c_duration = av_rescale_q(format_ctx->duration, av_tb, ms_tb);

        duration = v_duration;
        if (duration < 0 || almost_equal(v_duration, 0)) {
            /* fallback to the container duration if the video stream
             * doesnt report anything */
            duration = c_duration;
        }

        AVCodecContext *v_codec_ctx = format_ctx->streams[v_stream_idx]->codec;

        w = v_codec_ctx->width;
        h = v_codec_ctx->height;

        rational_rate = format_ctx->streams[v_stream_idx]->avg_frame_rate;
        rate = rational_rate.num * 1.0 / rational_rate.den;

        /* calculate num of frames ourselves */
        frames = rate * duration / 1000.0;

        /* if sample aspect ratio is unknown assume it is 1:1 */
        sar = format_ctx->streams[v_stream_idx]->sample_aspect_ratio;
        if (sar.num == 0) {
            sar.num = 1;
            sar.den = 1;
        }

        /* the display aspect ratio can be calculated from the pixel aspect
         * ratio and sample aspect ratio: PAR * SAR = DAR.*/
        int dar_n = w * sar.num;
        int dar_d = h * sar.den;
        int g = gcd(dar_n, dar_d);  /* use gcd to reduce to simplest terms */

        dar.num = dar_n / g;
        dar.den = dar_d / g;
    }

    av_log_set_level(initial_level);  /* reset */

    /* An avformat_free_context call is not needed because avformat_close_input
     * will automatically perform file cleanup and free everything associated
     * with the file. Calling free after close will trigger a segfault for for
     * those using Libav */
    avformat_close_input(&format_ctx);

    /* create dictionary with video information */
    py_info = PyDict_New();

    py_safe_set(py_info, "path", PyString_FromString(path));
    py_safe_set(py_info, "v_stream_exists", PyBool_FromLong(v_stream_exists));
    py_safe_set(py_info, "a_stream_exists", PyBool_FromLong(a_stream_exists));
    py_safe_set(py_info, "s_stream_exists", PyBool_FromLong(s_stream_exists));
    py_safe_set(py_info, "w", PyInt_FromLong(w));
    py_safe_set(py_info, "h", PyInt_FromLong(h));
    py_safe_set(py_info, "sar_n", PyInt_FromLong(sar.num));
    py_safe_set(py_info, "sar_d", PyInt_FromLong(sar.den));
    py_safe_set(py_info, "dar_n", PyInt_FromLong(dar.num));
    py_safe_set(py_info, "dar_d", PyInt_FromLong(dar.den));
    py_safe_set(py_info, "duration", PyFloat_FromDouble(duration));
    py_safe_set(py_info, "rate_n", PyInt_FromLong(rational_rate.num));
    py_safe_set(py_info, "rate_d", PyInt_FromLong(rational_rate.den));
    py_safe_set(py_info, "rate", PyFloat_FromDouble(rate));
    py_safe_set(py_info, "frames", PyLong_FromUnsignedLong(frames));

    return py_info;
}

static PyObject*
print_av_info(PyObject *self, PyObject *arg) {
    PyObject *py_info = get_av_info(self, arg);

    if (py_info == NULL) {
        return (PyObject*)NULL;
    }

    /* get list of streams as a string */
    char streams[32] = "";  /* must be initialized for strncat */
    int prev_exists = 0;
    /* PyDict_GetItemString returns borrowed refs */
    if (PyObject_IsTrue(PyDict_GetItemString(py_info, "v_stream_exists"))) {
        strncat(streams, "video", 5);
        prev_exists = 1;
    }
    if (PyObject_IsTrue(PyDict_GetItemString(py_info, "a_stream_exists"))) {
        if (prev_exists) {
            strncat(streams, ",", 1);
        }
        strncat(streams, "audio", 5);
        prev_exists = 1;
    }
    if (PyObject_IsTrue(PyDict_GetItemString(py_info, "s_stream_exists"))) {
        if (prev_exists) {
            strncat(streams, ",", 1);
        }
        strncat(streams, "subtitle", 8);
    }

    /* get values for time string */
    int x;
    int hrs, mins, secs;
    float duration = PyFloat_AsDouble(PyDict_GetItemString(py_info,
                                                           "duration"));
    x = duration / 1000.0;
    secs = x % 60;
    x /= 60;
    mins = x % 60;
    x /= 60;
    hrs = x % 24;

    printf("Video information:");
    printf("\n  Streams available  \t: %s"
           "\n  Resolution         \t: %dx%d, SAR %d:%d DAR %d:%d"
           "\n  Rate               \t: %.3f fps"
           "\n  Duration           \t: %02d:%02d:%02d (%.2fs)"
           "\n  Num of frames      \t: %lu\n",
        streams,
        (int)PyInt_AsLong(PyDict_GetItemString(py_info, "w")),
        (int)PyInt_AsLong(PyDict_GetItemString(py_info, "h")),
        (int)PyInt_AsLong(PyDict_GetItemString(py_info, "sar_n")),
        (int)PyInt_AsLong(PyDict_GetItemString(py_info, "sar_d")),
        (int)PyInt_AsLong(PyDict_GetItemString(py_info, "dar_n")),
        (int)PyInt_AsLong(PyDict_GetItemString(py_info, "dar_d")),
        (float)PyFloat_AsDouble(PyDict_GetItemString(py_info, "rate")),
        hrs, mins, secs,
        duration / 1000.0,
        PyInt_AsUnsignedLongMask(PyDict_GetItemString(py_info, "frames")));

    Py_DECREF(py_info);
    Py_RETURN_NONE;
}

static PyMethodDef ModuleMethods[] = {
    {"get_av_info", get_av_info, METH_O,
        "Return information on a multimedia file as a dictionary"},
    {"print_av_info", print_av_info, METH_O,
        "Prints a multimedia file's information"},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initavinfo(void) {
    (void)Py_InitModule("avinfo", ModuleMethods);
}
