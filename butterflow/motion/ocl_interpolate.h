#ifndef OCL_INTERPOLATE_H
#define OCL_INTERPOLATE_H

#include <stdio.h>
#include <opencv2/core/core.hpp>
using namespace std;
using namespace cv;

vector<Mat>
ocl_interpolate_flow(Mat& fr_1, Mat& fr_2, Mat& fu, Mat& fv, Mat& bu,
    Mat& bv, float time_step);

#endif
