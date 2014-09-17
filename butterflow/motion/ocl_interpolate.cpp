#include "ocl_interpolate.h"
#include <opencv2/ocl/ocl.hpp>

using namespace std;
using namespace cv;
using namespace cv::ocl;

vector<Mat>
ocl_interpolate_flow(Mat& fr_1, Mat& fr_2, Mat& fu, Mat& fv, Mat& bu,
  Mat& bv, float time_step) {
  oclMat fr_1_b, fr_1_g, fr_1_r;
  oclMat fr_2_b, fr_2_g, fr_2_r;

  Mat chans[3];

  cv::split(fr_1, chans);
  fr_1_b.upload(chans[0]);
  fr_1_g.upload(chans[1]);
  fr_1_r.upload(chans[2]);

  cv::split(fr_2, chans);
  fr_2_b.upload(chans[0]);
  fr_2_g.upload(chans[1]);
  fr_2_r.upload(chans[2]);

  oclMat ocl_fu(fu);
  oclMat ocl_fv(fv);
  oclMat ocl_bu(bu);
  oclMat ocl_bv(bv);

  vector<Mat> new_frs;

  oclMat buf;
  oclMat new_b, new_g, new_r;
  oclMat new_fr;

  for (float x = time_step; x < 1.0; x += time_step) {
    interpolateFrames(fr_1_b, fr_2_b, ocl_fu, ocl_fv, ocl_bu, ocl_bv, x, new_b, buf);
    interpolateFrames(fr_1_g, fr_2_g, ocl_fu, ocl_fv, ocl_bu, ocl_bv, x, new_g, buf);
    interpolateFrames(fr_1_r, fr_2_r, ocl_fu, ocl_fv, ocl_bu, ocl_bv, x, new_r, buf);

    oclMat chans[] = {new_b, new_g, new_r};
    merge(chans, 3, new_fr);

    Mat ret_mat;
    new_fr.download(ret_mat);
    ret_mat.convertTo(ret_mat, CV_8UC3, 255.0);
    new_frs.push_back(ret_mat);
  }

  return new_frs;
}
