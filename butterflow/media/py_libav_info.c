#include <Python.h>
#include "py_libav_info.h"
#include <stdio.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/mathematics.h>

#define MIN(a,b) (((a)<(b))?(a):(b))
#define MAX(a,b) (((a)>(b))?(a):(b))
#define MS_PER_SEC 1000


static PyObject*
py_get_video_info(PyObject *self, PyObject *arg) {
  char *vid_path = PyString_AsString(arg);

  av_register_all();

  AVFormatContext *format_ctx = avformat_alloc_context();

  int ret = avformat_open_input(&format_ctx, vid_path, NULL, NULL);
  if (ret != 0) {
    printf("av: could not open input");
    Py_RETURN_NONE;
  }
  ret = avformat_find_stream_info(format_ctx, NULL);
  if (ret < 0) {
    printf("av: could not find stream");
    Py_RETURN_NONE;
  }

  int v_stream_idx = av_find_best_stream(format_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
  int a_stream_idx = av_find_best_stream(format_ctx, AVMEDIA_TYPE_AUDIO, -1, -1, NULL, 0);
  int s_stream_idx = av_find_best_stream(format_ctx, AVMEDIA_TYPE_SUBTITLE, -1, -1, NULL, 0);

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
  unsigned long num_frames = 0;

  if (v_stream_exists) {
    AVStream *v_stream = format_ctx->streams[v_stream_idx];

    AVRational ms_tb = {1, MS_PER_SEC};
    AVRational av_tb = {1, AV_TIME_BASE};

    v_duration = av_rescale_q(v_stream->duration, v_stream->time_base, ms_tb);
    c_duration = av_rescale_q(format_ctx->duration, av_tb, ms_tb);

    duration = MAX(v_duration, c_duration);

    AVCodecContext *v_codec_ctx = format_ctx->streams[v_stream_idx]->codec;

    w = v_codec_ctx->width;
    h = v_codec_ctx->height;

    AVRational rational_rate = format_ctx->streams[v_stream_idx]->r_frame_rate;

    rate_num = rational_rate.num;
    rate_den = rational_rate.den;
    double rate = rate_num*1.0/rate_den;

    num_frames = rate * (duration / 1000.0);
    min_rate   = num_frames/ (duration / 1000.0);
  }

  avformat_close_input(&format_ctx);
  avformat_free_context(format_ctx);

  PyObject *py_info = PyList_New(10);

  PyList_SetItem(py_info, 0, PyBool_FromLong(v_stream_exists));
  PyList_SetItem(py_info, 1, PyBool_FromLong(a_stream_exists));
  PyList_SetItem(py_info, 2, PyBool_FromLong(s_stream_exists));
  PyList_SetItem(py_info, 3, PyInt_FromLong(w));
  PyList_SetItem(py_info, 4, PyInt_FromLong(h));
  PyList_SetItem(py_info, 5, PyFloat_FromDouble(duration));
  PyList_SetItem(py_info, 6, PyInt_FromLong(rate_num));
  PyList_SetItem(py_info, 7, PyInt_FromLong(rate_den));
  PyList_SetItem(py_info, 8, PyFloat_FromDouble(min_rate));
  PyList_SetItem(py_info, 9, PyInt_FromLong(num_frames));
  return py_info;
}

static PyMethodDef ModuleMethods[] = {
  {"py_get_video_info", py_get_video_info, METH_O, ""},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initpy_libav_info(void) {
  (void)Py_InitModule("py_libav_info", ModuleMethods);
}
