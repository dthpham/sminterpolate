#ifndef OCL_OPTICAL_FLOW_H
#define OCL_OPTICAL_FLOW_H

#include <opencv2/core/core.hpp>
using namespace cv;

vector<Mat>
ocl_farneback_optical_flow(Mat& fr_1, Mat& fr_2, double scale, int levels,
    int winsize, int iters, int poly_n, double poly_sigma, bool fast_pyramids,
    int flags);

#endif
