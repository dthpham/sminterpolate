# Author: Duong Pham
# Copyright 2015

import cv2
import sys
import collections
import inspect
from butterflow.settings import default as s
from butterflow.__init__ import __version__


def draw_progress_bar(img, p):
    h = img.shape[0]
    w = img.shape[1]
    p = float(p)

    draw_rect = lambda x, y: \
        cv2.rectangle(img, x, y, s['bar_color'], s['ln_type'])
    # `shift_*` is how much to shift horiz and vert. `ext_*`` is how much to
    # extend the vertices
    draw_strk = lambda x, y, shift_x, shift_y, ext_x, ext_y: \
        cv2.rectangle(img, (x[0] + shift_x - ext_x, x[1] + shift_y - ext_y),
                      (y[0] + shift_x + ext_x, y[1] + shift_y + ext_y),
                      s['bar_strk_color'], s['ln_type'])

    # draw four lines that make up the outer rectangle that outline the bar
    # origin is at the top left, points go from right then down. vertex 1 (x,y)
    # is at the top left of rectangle, v2 is bottom right - the opposite end of
    # the rect
    top_v1 = (int(w * s['bar_s_pad']), int(h * s['bar_t_pad']))
    top_v2 = (int(w * (1 - s['bar_s_pad'])), top_v1[1] + s['ln_thick'])
    draw_strk(top_v1, top_v2, 0, -s['strk_sz'], 1, 0)
    draw_rect(top_v1, top_v2)

    bot_v1 = (top_v1[0], top_v2[1] + 2 * s['bar_in_pad'] + s['bar_thick'])
    bot_v2 = (top_v2[0], bot_v1[1] + s['ln_thick'])
    draw_strk(bot_v1, bot_v2, 0, s['strk_sz'], 1, 0)
    draw_rect(bot_v1, bot_v2)

    left_v1 = top_v1
    left_v2 = (bot_v1[0] + s['ln_thick'], bot_v1[1] + s['ln_thick'])
    draw_strk(left_v1, left_v2, -s['strk_sz'], 0, 0, 0)
    draw_rect(left_v1, left_v2)

    right_v1 = (top_v2[0] - s['ln_thick'], top_v1[1])
    right_v2 = bot_v2
    draw_strk(right_v1, right_v2, s['strk_sz'], 0, 0, 0)
    draw_rect(right_v1, right_v2)

    # draw the progress bar inside the rectangle
    pad = s['ln_thick'] + s['bar_in_pad']
    max_w = int(right_v2[0] - pad)
    min_w = int(left_v1[0] + pad)
    bar_v1 = (top_v1[0] + pad, left_v1[1] + pad)
    bar_v2 = (max(min_w, min(max_w, int(max_w * p))), bot_v2[1] - pad)
    if p > 0:
        draw_strk(bar_v1, bar_v2, 0, 0, 1, 1)  # draw a complete outline
        draw_rect(bar_v1, bar_v2)


def draw_debug_text(img, text_type, rate, flow_function, tot_frs_wrt, pair_a,
                    pair_b, btw_idx, fr_type, is_dup, tgt_frs, frs_wrt,
                    sub, sub_idx, subs_to_render, drp_every,
                    dup_every, src_seen, frs_int, frs_drp, frs_dup):
    h = img.shape[0]
    w = img.shape[1]

    scale = min(min(float(w) / s['h_fits'], 1.0),
                min(float(h) / s['v_fits'], 1.0))
    if scale < s['txt_min_scale']:
        return  # don't draw if the image is too small to draw the font on

    if text_type in ['light', 'stroke']:
        color = s['light_color']
    else:
        color = s['dark_color']

    draw_strk = lambda x, y: \
        cv2.putText(img, x, y, s['font_face'], scale, s['dark_color'],
                    s['strk_thick'], s['font_type'])
    draw_text = lambda x, y: \
        cv2.putText(img, x, y, s['font_face'], scale, color,
                    s['txt_thick'], s['font_type'])

    txt = "butterflow {} ({})\n"\
          "Res: {},{}\n"\
          "Playback Rate: {:.2f} fps\n"
    txt = txt.format(__version__, sys.platform, w, h, rate)

    argspec = inspect.getargspec(flow_function)
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
            flow_format += ("{}: " + value_format).format(k.capitalize(), v)
            if i == len(flow_kwargs) - 1:
                flow_format += '\n\n'
            else:
                flow_format += ', '
            i += 1
        txt += flow_format

    txt += "Frame: {}\n"\
           "Pair Index: {}, {}, {}\n"\
           "Type Src: {}, Int: {}, Dup: {}\n"\
           "Mem: {}\n"
    txt = txt.format(tot_frs_wrt,
                     pair_a,
                     pair_b,
                     btw_idx,
                     'Y' if fr_type == 'source' else 'N',
                     'Y' if fr_type == 'interpolated' else 'N',
                     'Y' if is_dup > 0 else 'N',
                     hex(id(img)))

    for line_idx, line in enumerate(txt.split('\n')):
        line_sz, _ = cv2.getTextSize(line, s['font_face'], scale,
                                     s['txt_thick'])
        _, line_h = line_sz
        origin = (int(s['txt_l_pad']), int(s['txt_t_pad'] +
                  (line_idx * (line_h + s['txt_ln_b_pad']))))
        if text_type == 'stroke':
            draw_strk(line, origin)
        draw_text(line, origin)

    txt = "Region {}/{} F: [{}, {}] T: [{:.2f}s, {:.2f}s]\n"\
          "Len F: {}, T: {:.2f}s\n"
    txt = txt.format(sub_idx + 1,
                     subs_to_render,
                     sub.fa,
                     sub.fb,
                     sub.ta / 1000.0,
                     sub.tb / 1000.0,
                     (sub.fb - sub.fa) + 1,
                     (sub.tb - sub.ta) / 1000.0)

    def fsorp(f, v):
        if v is None:
            return s['txt_placeh']
        return f.format(v)

    txt += "Target Spd: {} Dur: {} Fps: {}\n"
    txt = txt.format(fsorp('{:.2f}', sub.spd),
                     fsorp('{:.2f}s', sub.dur / 1000.0) if sub.dur
                           else s['txt_placeh'],
                     fsorp('{}', sub.fps))

    txt += "Out Len F: {}, Dur: {:.2f}s\n"\
           "Drp every {:.1f}, Dup every {:.1f}\n"\
           "Src seen: {}, Int: {}, Drp: {}, Dup: {}\n"\
           "Write Ratio: {}/{} ({:.2f}%)\n"
    txt = txt.format(tgt_frs,
                     tgt_frs / float(rate),
                     drp_every,
                     dup_every,
                     src_seen,
                     frs_int,
                     frs_drp,
                     frs_dup,
                     frs_wrt,
                     tgt_frs,
                     frs_wrt * 100.0 / tgt_frs)

    for line_idx, line in enumerate(txt.split('\n')):
        line_sz, _ = cv2.getTextSize(line, s['font_face'], scale,
                                     s['txt_thick'])
        line_w, line_h = line_sz
        origin = (int(w - s['txt_r_pad'] - line_w),
                  int(s['txt_t_pad'] +
                  (line_idx * (line_h + s['txt_ln_b_pad']))))
        if text_type == 'stroke':
            draw_strk(line, origin)
        draw_text(line, origin)
