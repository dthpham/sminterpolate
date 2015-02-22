#include "ocl_optical_flow.h"
#include <opencv2/ocl/ocl.hpp>
#include <opencv2/video/tracking.hpp>

using namespace cv;
using namespace cv::ocl;

vector<Mat>
ocl_farneback_optical_flow(Mat& fr_1, Mat& fr_2, double scale, int levels,
  int winsize, int iters, int poly_n, double poly_sigma, bool fast_pyramids,
  int flags) {

  FarnebackOpticalFlow calc_flow;
  calc_flow.numLevels = levels;
  calc_flow.pyrScale  = scale;
  calc_flow.winSize   = winsize;
  calc_flow.numIters  = iters;
  calc_flow.polyN     = poly_n;
  calc_flow.polySigma = poly_sigma;
  calc_flow.fastPyramids = fast_pyramids;
  calc_flow.flags     = flags;

  oclMat ocl_fr_1(fr_1);
  oclMat ocl_fr_2(fr_2);
  oclMat ocl_flow_x;
  oclMat ocl_flow_y;

  calc_flow(ocl_fr_1, ocl_fr_2, ocl_flow_x, ocl_flow_y);

  calc_flow.releaseMemory();

  vector<Mat> flows;
  flows.push_back(ocl_flow_x);
  flows.push_back(ocl_flow_y);

  return flows;
}
