// Author: Duong Pham
// Copyright 2015

#include <Python.h>
#include <stdio.h>
#include <string.h>
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

struct AvInfo {
    int v_stream_exists;
    int a_stream_exists;
    int s_stream_exists;
    int w;
    int h;
    AVRational sar;
    AVRational dar;
    int64_t duration;
    unsigned long frames;
    AVRational rate;
};

int gcd(int a, int b) {
    return b == 0 ? a : gcd(b, a % b);
}

int mk_av_info_struct(char *file, struct AvInfo *av_info) {
    av_register_all();

    AVFormatContext *format_ctx = avformat_alloc_context();

    /* make quiet. should reset when finished */
    int initial_level = av_log_get_level();
    av_log_set_level(AV_LOG_ERROR);

    int rc = avformat_open_input(&format_ctx, file, NULL, NULL);
    if (rc != 0) {
        return -1;
    }

    rc = avformat_find_stream_info(format_ctx, NULL);
    if (rc < 0) {
        avformat_close_input(&format_ctx);
        return -1;
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
    AVRational rate = {0, 0};  /* average fps */

    if (v_stream_exists) {
        AVStream *v_stream = format_ctx->streams[v_stream_idx];

        AVRational ms_tb = {1, MS_PER_SEC};
        AVRational av_tb = {1, AV_TIME_BASE};

        int64_t v_stream_duration  = av_rescale_q(v_stream->duration,
                                                  v_stream->time_base,
                                                  ms_tb);
        int64_t container_duration = av_rescale_q(format_ctx->duration,
                                                  av_tb, ms_tb);

        duration = v_stream_duration;
        if (v_stream_duration == 0) {
            /* fallback to the container duration if the video stream doesnt
             * report anything */
            duration = container_duration;
        }

        AVCodecContext *v_codec_ctx = format_ctx->streams[v_stream_idx]->codec;

        w = v_codec_ctx->width;
        h = v_codec_ctx->height;

        rate = format_ctx->streams[v_stream_idx]->avg_frame_rate;

        frames = (rate.num * 1.0 / rate.den) * (duration / 1000.0);

        /* the display aspect ratio can be calculated from the pixel aspect
         * ratio and sample aspect ratio: PAR * SAR = DAR */
        sar = format_ctx->streams[v_stream_idx]->sample_aspect_ratio;
        dar = format_ctx->streams[v_stream_idx]->display_aspect_ratio;

        /* if sar is unknown assume it is 1:1 */
        if (sar.num == 0) {
            sar.num = 1;
            sar.den = 1;
        }
        /* calculate dar by hand if it is unknown. it should be reduced to
         * it's simplest terms */
        if (dar.num == 0) {
            int dar_n = w * sar.num;
            int dar_d = h * sar.den;
            int g = gcd(dar_n, dar_d);

            dar.num = dar_n / g;
            dar.den = dar_d / g;
        }
    }

    av_log_set_level(initial_level);

    /* An avformat_free_context call is not needed because avformat_close_input
     * will automatically perform file cleanup and free everything associated
     * with the file. Calling free after close will trigger a segfault for for
     * those using Libav */
    avformat_close_input(&format_ctx);

    av_info->v_stream_exists = v_stream_exists;
    av_info->a_stream_exists = a_stream_exists;
    av_info->s_stream_exists = s_stream_exists;
    av_info->w = w;
    av_info->h = h;
    av_info->sar = sar;
    av_info->dar = dar;
    av_info->duration = duration;
    av_info->frames = frames;
    av_info->rate = rate;

    return 0;
}


static PyObject*
print_av_info(PyObject *self, PyObject *arg) {
    char *file = PyString_AsString(arg);
    struct AvInfo av_info;

    if (mk_av_info_struct(file, &av_info) < 0) {
        PyErr_SetString(PyExc_RuntimeError, "could not retreive info");
        Py_RETURN_NONE;
    }

    /* get list of streams */
    char streams[32] = "";  /* must be initialized for strncat */
    if (av_info.v_stream_exists) {
        strncat(streams, "video", 5);
    }
    if (av_info.a_stream_exists) {
        strncat(streams, ",audio", 6);
    }
    if (av_info.s_stream_exists) {
        strncat(streams, ",subtitle", 9);
    }

    /* get friendly time string */
    int x;
    int secs;
    int mins;
    int hrs;

    x = (float)av_info.duration / 1000.0;
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
        av_info.w,
        av_info.h,
        av_info.sar.num,
        av_info.sar.den,
        av_info.dar.num,
        av_info.dar.den,
        av_info.rate.num * 1.0 / av_info.rate.den,
        hrs, mins, secs,
        (float)av_info.duration / 1000.0,
        av_info.frames);

    Py_RETURN_NONE;
}

static PyObject*
get_av_info(PyObject *self, PyObject *arg) {
    char *file = PyString_AsString(arg);
    struct AvInfo av_info;
    PyObject *py_info;

    if (mk_av_info_struct(file, &av_info) < 0) {
        PyErr_SetString(PyExc_RuntimeError, "could not retreive info");
        return (PyObject*)NULL;
    }

    /* create dictionary with video information */
    py_info = PyDict_New();

    py_safe_set(py_info, "path", PyString_FromString(file));
    py_safe_set(py_info, "v_stream_exists", PyBool_FromLong(av_info.v_stream_exists));
    py_safe_set(py_info, "a_stream_exists", PyBool_FromLong(av_info.a_stream_exists));
    py_safe_set(py_info, "s_stream_exists", PyBool_FromLong(av_info.s_stream_exists));
    py_safe_set(py_info, "w", PyInt_FromLong(av_info.w));
    py_safe_set(py_info, "h", PyInt_FromLong(av_info.h));
    py_safe_set(py_info, "sar_n", PyInt_FromLong(av_info.sar.num));
    py_safe_set(py_info, "sar_d", PyInt_FromLong(av_info.sar.den));
    py_safe_set(py_info, "dar_n", PyInt_FromLong(av_info.dar.num));
    py_safe_set(py_info, "dar_d", PyInt_FromLong(av_info.dar.den));
    py_safe_set(py_info, "duration", PyFloat_FromDouble(av_info.duration));
    py_safe_set(py_info, "rate_n", PyInt_FromLong(av_info.rate.num));
    py_safe_set(py_info, "rate_d", PyInt_FromLong(av_info.rate.den));
    py_safe_set(py_info, "frames", PyInt_FromLong(av_info.frames));

    return py_info;
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
