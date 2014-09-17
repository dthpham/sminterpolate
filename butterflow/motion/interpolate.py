import py_motion as py_motion


class Interpolate:
  '''a collection of interpolation functions'''
  @staticmethod
  def validate_time_step(ts):
    if ts <= 0 or ts > 1:
      raise ValueError('time_step {} not between (0,1]'.format(ts))

  @staticmethod
  def interpolate_frames_ocl(fr_1, fr_2, fu, fv, bu, bv, time_step):
    '''interpolates frames using the provided flows/displacement
    fields. returns a list of numpy.ndarrays. leverages the opencl
    framework.
    '''
    Interpolate.validate_time_step(time_step)
    return py_motion.py_ocl_interpolate_flow(
        fr_1, fr_2, fu, fv, bu, bv, time_step)

  @staticmethod
  def interpolate_frames(fr_1, fr_2, fu, fv, bu, bv, time_step):
    pass
