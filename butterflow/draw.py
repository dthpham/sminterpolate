# -*- coding: utf-8 -*-

import cv2
import sys
import collections
import inspect
from butterflow.settings import default as settings
from butterflow.__init__ import __version__


def draw_if_fr_fits(w_fits, h_fits, min_scale):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            fr = args[0]
            scale = min(float(fr.shape[1]) / float(w_fits),
                        float(fr.shape[0]) / float(h_fits))
            if scale >= min_scale:
                return fn(*args, **kwargs)
            else:
                return None
        return wrapper
    return decorator


@draw_if_fr_fits(settings['mrk_w_fits'], settings['mrk_h_fits'], 1.0)
def draw_marker(fr, fill=True):
    w = fr.shape[1]
    h = fr.shape[0]
    x = int(w - (settings['mrk_r_pad'] + settings['mrk_out_radius']))
    y = int(h - settings['mrk_d_pad'] - settings['mrk_out_radius'])
    cv2.circle(fr,
               (x, y),
               settings['mrk_out_radius'],
               settings['mrk_out_color'],
               settings['mrk_out_thick'],
               settings['mrk_ln_type'])
    color = settings['mrk_color']
    if fill:
        color = settings['mrk_fill_color']
    cv2.circle(fr,
               (x, y),
               settings['mrk_in_radius'],
               color,
               settings['mrk_in_thick'],
               settings['mrk_ln_type'])


@draw_if_fr_fits(settings['bar_w_fits'], settings['bar_h_fits'], 1.0)
def draw_progress_bar(fr, progress=0.0):
    w = fr.shape[1]
    h = fr.shape[0]

    def draw_stroke(x, y, shift_x, shift_y, extend_x, extend_y):
        cv2.rectangle(fr,
                      (x[0] + shift_x - extend_x, x[1] + shift_y - extend_y),
                      (y[0] + shift_x + extend_x, y[1] + shift_y + extend_y),
                      settings['bar_stroke_color'],
                      settings['bar_ln_type'])

    def draw_rectangle(x, y):
        cv2.rectangle(fr,
                      x,
                      y,
                      settings['bar_color'],
                      settings['bar_ln_type'])

    t_v1 = (int(w * settings['bar_s_pad']), int(h * settings['bar_t_pad']))
    t_v2 = (int(w * (1 - settings['bar_s_pad'])), t_v1[1] +
            settings['bar_ln_thick'])

    draw_stroke(t_v1, t_v2, 0, -settings['bar_stroke_thick'], 1, 0)
    draw_rectangle(t_v1, t_v2)

    b_v1 = (t_v1[0], t_v2[1] + 2 * settings['bar_in_pad'] +
            settings['bar_thick'])
    b_v2 = (t_v2[0], b_v1[1] + settings['bar_ln_thick'])

    draw_stroke(b_v1, b_v2, 0, settings['bar_stroke_thick'], 1, 0)
    draw_rectangle(b_v1, b_v2)

    l_v1 = t_v1
    l_v2 = (b_v1[0] + settings['bar_ln_thick'], b_v1[1] +
            settings['bar_ln_thick'])

    draw_stroke(l_v1, l_v2, -settings['bar_stroke_thick'], 0, 0, 0)
    draw_rectangle(l_v1, l_v2)

    r_v1 = (t_v2[0] - settings['bar_ln_thick'], t_v1[1])
    r_v2 = b_v2

    draw_stroke(r_v1, r_v2, settings['bar_stroke_thick'], 0, 0, 0)
    draw_rectangle(r_v1, r_v2)

    pad = settings['bar_ln_thick'] + settings['bar_in_pad']
    max_w = int(r_v2[0] - pad)
    min_w = int(l_v1[0] + pad)
    bar_v1 = (t_v1[0] + pad, l_v1[1] + pad)
    bar_v2 = (max(min_w, min(max_w, int(max_w * progress))), b_v2[1] - pad)

    if progress > 0:
        draw_stroke(bar_v1, bar_v2, 0, 0, 1, 1)
        draw_rectangle(bar_v1, bar_v2)


@draw_if_fr_fits(settings['txt_w_fits'], settings['txt_h_fits'], settings['txt_min_scale'])
def draw_debug_text(fr, text_type, rate, optflow_fn, tot_frs_written, pair_a,
                    pair_b, idx_between_pair, fr_type, is_dupe, frs_to_render,
                    frs_written, sub, sub_idx, subs_to_render, drp_every,
                    dup_every, src_seen, frs_interpolated, frs_dropped,
                    frs_duped):
    w = fr.shape[1]
    h = fr.shape[0]
    min_w = min(float(w)/settings['txt_w_fits'], settings['txt_max_scale'])
    min_h = min(float(h)/settings['txt_h_fits'], settings['txt_max_scale'])
    scale = min(min_w, min_h)

    def draw_stroke(x, y):
        cv2.putText(fr,
                    x,
                    y,
                    settings['font_face'],
                    scale,
                    settings['dark_color'],
                    settings['txt_stroke_thick'],
                    settings['font_type'])

    if text_type == 'dark':
        color = settings['dark_color']
    else:
        color = settings['light_color']

    def draw_text(x, y):
        cv2.putText(fr,
                    x,
                    y,
                    settings['font_face'],
                    scale,
                    color,
                    settings['txt_thick'],
                    settings['font_type'])

    txt = "butterflow {} ({})\n"\
          "Res: {}x{}\n"\
          "Playback Rate: {:.2f} fps\n"
    txt = txt.format(__version__, sys.platform, w, h, rate)

    argspec = inspect.getargspec(optflow_fn)
    defaults = list(argspec.defaults)
    args = argspec.args[-len(defaults):]
    flow_kwargs = collections.OrderedDict(zip(args, defaults))

    if flow_kwargs is not None:
        flow_format = ''
        i = 0
        for k, v in flow_kwargs.items():
            value_format = "{}"
            if isinstance(v, bool):
                value_format = "{:1}"
            flow_format += ("{}: "+value_format).format(k.capitalize()[:1], v)
            if i == len(flow_kwargs)-1:
                flow_format += '\n\n'
            else:
                flow_format += ', '
            i += 1
        txt += flow_format

    def yn_str(bool):
        if bool:
            return 'Y'
        else:
            return 'N'

    txt += "Frame: {}\n"\
           "Pair Index: {}, {}, {}\n"\
           "Type Src: {}, Int: {}, Dup: {}\n"\
           "Mem: {}\n"
    txt = txt.format(tot_frs_written,
                     pair_a,
                     pair_b,
                     idx_between_pair,
                     yn_str(fr_type == 'SOURCE'),
                     yn_str(fr_type == 'INTERPOLATED'),
                     yn_str(is_dupe > 0),
                     hex(id(fr)))

    for i, line in enumerate(txt.split('\n')):
        line_sz, _ = cv2.getTextSize(line,
                                     settings['font_face'],
                                     scale,
                                     settings['txt_thick'])
        _, line_h = line_sz
        origin = (int(settings['txt_l_pad']), int(settings['txt_t_pad'] +
                  (i * (line_h + settings['txt_ln_b_pad']))))
        if text_type == 'stroke':
            draw_stroke(line, origin)
        draw_text(line, origin)

    txt = "Region {}/{}, F: [{}, {}], T: [{:.2f}, {:.2f}s]\n"\
          "Len F: {}, T: {:.2f}s\n"
    txt = txt.format(sub_idx,
                     subs_to_render,
                     sub.fa,
                     sub.fb,
                     sub.ta / 1000.0,
                     sub.tb / 1000.0,
                     (sub.fb - sub.fa) + 1,
                     (sub.tb - sub.ta) / 1000.0)

    def str_or_placeholder(str_fmt, str):
        if str is None:
            return settings['txt_placeh']
        return str_fmt.format(str)

    txt += "Target Spd: {} Dur: {} Fps: {}\n"
    txt = txt.format(str_or_placeholder('{:.2f}', sub.target_spd),
                     str_or_placeholder('{:.2f}s', sub.target_dur / 1000.0)
                     if sub.target_dur else settings['txt_placeh'],
                     str_or_placeholder('{:.2f}', sub.target_fps))
    txt += "Out Len F: {}, T: {:.2f}s\n"\
           "Drp every {:.1f}, Dup every {:.1f}\n"\
           "Src seen: {}, Int: {}, Drp: {}, Dup: {}\n"\
           "Write Ratio: {}/{} ({:.2f}%)\n"
    txt = txt.format(frs_to_render,
                     frs_to_render / float(rate),
                     drp_every,
                     dup_every,
                     src_seen,
                     frs_interpolated,
                     frs_dropped,
                     frs_duped,
                     frs_written,
                     frs_to_render,
                     frs_written * 100.0 / frs_to_render)

    for i, line in enumerate(txt.split('\n')):
        line_sz, _ = cv2.getTextSize(line,
                                     settings['font_face'],
                                     scale,
                                     settings['txt_thick'])
        line_w, line_h = line_sz
        origin = (int(w - settings['txt_r_pad'] - line_w),
                  int(settings['txt_t_pad'] +
                  (i * (line_h + settings['txt_ln_b_pad']))))
        if text_type == 'stroke':
            draw_stroke(line, origin)
        draw_text(line, origin)
