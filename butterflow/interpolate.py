# Author: Duong Pham
# a parallel, naive implementation of software frame interpolation using
# provided optical flows (displacement fields)

import numpy as np
import multiprocessing
from itertools import izip
import signal

def time_steps_for_int_frames(n):  # python version
    sub_divisions = n + 1
    time_steps = []
    for i in range(n):
        ts = max(0.0, min(1.0, (1.0 / sub_divisions) * (i + 1)))
        time_steps.append(ts)
    return time_steps

def fr_at_time_step(target_fr, u, v, ts, name=''):
    shape = target_fr.shape
    fr = np.zeros(shape, dtype=np.float32)
    for idx in np.ndindex(shape):
        py = idx[0] + v[idx[0], idx[1]] * ts
        px = idx[1] + u[idx[0], idx[1]] * ts
        ch = idx[2]
        fr[idx] = target_fr[np.clip(np.rint(py), 0, shape[0]-1),
                            np.clip(np.rint(px), 0, shape[1]-1), ch]
    return ts, name, fr

def fr_at_time_step_wrp(args):   # to pass multiple args for Pool.map
    return fr_at_time_step(*args)

def init_worker():  # captures ctrl+c
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def sw_interpolate_flow(prev_fr, next_fr, fu, fv, bu, bv, int_each_go):
    frs = []
    time_steps = time_steps_for_int_frames(int_each_go)
    cpus = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(multiprocessing.cpu_count(), init_worker)
    work_steps = cpus / 2
    try:
        for i in range(0, len(time_steps), work_steps):
            def blend_results(*args):
                results = args[0]
                def pairwise(iterable):
                    a = iter(iterable)
                    return izip(a, a)
                for n, p in pairwise(results):
                    def alpha_blend(a, b, alpha):
                        return (1-alpha)*a + alpha*b
                    bfr = alpha_blend(n[2], p[2], n[0])
                    bfr = (bfr*255.0).astype(np.uint8)
                    frs.append(bfr)
            task_list = []
            for j in range(work_steps):
                if i+j > len(time_steps)-1:
                    continue
                ts = time_steps[i+j]
                task_list.extend([(next_fr, fu, fv, ts, 'next_fr'),
                                  (prev_fr, bu, bv, ts, 'prev_fr')])
            r = pool.map_async(fr_at_time_step_wrp, task_list,
                               callback=blend_results)
            r.wait()  # block on results, will return them in order
    except KeyboardInterrupt:
        pool.terminate()
        class KeyboardInterruptError(Exception): pass
        raise KeyboardInterruptError  # re-raise
    pool.close()
    return frs
