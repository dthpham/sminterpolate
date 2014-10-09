import os
import butterflow.motion.py_motion as py_motion
from butterflow.__init__ import cache_path

py_motion.py_ocl_set_cache_path(cache_path + os.sep)
