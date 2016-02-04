# draw debugging info on frs

import cv2
import sys
import collections
import inspect
from butterflow.settings import default as settings
from butterflow.__init__ import __version__

def draw_fr_marker(fr, fill=True):
    h = fr.shape[0]
    w = fr.shape[1]
    scale = min(float(w)/settings['mrk_w_fits'],
                float(h)/settings['mrk_h_fits'])
    if scale < 1.0:
        return

    center = (int(w - (settings['mrk_r_pad'] + settings['mrk_out_radius'])),
              int(h -  settings['mrk_d_pad'] - settings['mrk_out_radius']))

    cv2.circle(fr, center,  # outer circle
               settings['mrk_out_radius'],
               settings['mrk_out_color'],
               settings['mrk_out_thick'],
               settings['mrk_line_type'])
    cv2.circle(fr, center,  # flashing inner circle
               settings['mrk_in_radius'],
               settings['mrk_def_color'] if fill else settings['mrk_fill_color'],
               settings['mrk_in_thick'],
               settings['mrk_line_type'])

def draw_progress_bar(fr, progress=0.0):
    h = fr.shape[0]
    w = fr.shape[1]
    scale = min(float(w)/settings['bar_w_fits'],
                float(h)/settings['bar_h_fits'])
    if scale < 1.0:
        return

    # shift is how much to shift horizontally and vertically, ext is how much
    # to extend vertices
    draw_strk = lambda x, y, shift_x, shift_y, ext_x, ext_y: \
        cv2.rectangle(fr,
                      (x[0] + shift_x - ext_x, x[1] + shift_y - ext_y),
                      (y[0] + shift_x + ext_x, y[1] + shift_y + ext_y),
                      settings['bar_strk_color'],
                      settings['ln_type'])
    draw_rect = lambda x, y: \
        cv2.rectangle(fr, x, y,
                      settings['bar_color'],
                      settings['ln_type'])

    # Draw four lines of outer rect, points go r to d w/ origin at top left
    # v1 (x,y) is at the top left of the rect
    # v2 is bot right at opposite end of rect
    top_v1 = (int(w * settings['bar_s_pad']), int(h * settings['bar_t_pad']))
    top_v2 = (int(w * (1 - settings['bar_s_pad'])), top_v1[1] +
              settings['ln_thick'])
    draw_strk(top_v1, top_v2, 0, -settings['strk_sz'], 1, 0)
    draw_rect(top_v1, top_v2)

    bot_v1 = (top_v1[0], top_v2[1] + 2 * settings['bar_in_pad'] +
              settings['bar_thick'])
    bot_v2 = (top_v2[0], bot_v1[1] + settings['ln_thick'])
    draw_strk(bot_v1, bot_v2, 0, settings['strk_sz'], 1, 0)
    draw_rect(bot_v1, bot_v2)

    left_v1 = top_v1
    left_v2 = (bot_v1[0] + settings['ln_thick'], bot_v1[1] +
               settings['ln_thick'])
    draw_strk(left_v1, left_v2, -settings['strk_sz'], 0, 0, 0)
    draw_rect(left_v1, left_v2)

    right_v1 = (top_v2[0] - settings['ln_thick'], top_v1[1])
    right_v2 = bot_v2
    draw_strk(right_v1, right_v2, settings['strk_sz'], 0, 0, 0)
    draw_rect(right_v1, right_v2)

    # draw progress bar
    pad = settings['ln_thick'] + settings['bar_in_pad']
    max_w = int(right_v2[0] - pad)
    min_w = int(left_v1[0] + pad)
    bar_v1 = (top_v1[0] + pad, left_v1[1] + pad)
    bar_v2 = (max(min_w, min(max_w, int(max_w * progress))), bot_v2[1] - pad)

    if progress > 0:
        draw_strk(bar_v1, bar_v2, 0, 0, 1, 1)
        draw_rect(bar_v1, bar_v2)

def draw_debug_text(fr, text_type, rate, flow_fn, tot_frs_wrt, pair_a, pair_b,
                    btw_idx, fr_type, is_dup, tgt_frs, frs_wrt, sub, sub_idx,
                    subs_to_render, drp_every, dup_every, src_seen, frs_int,
                    frs_drp, frs_dup):
    h = fr.shape[0]
    w = fr.shape[1]
    scale = min(float(w)/settings['txt_w_fits'],
                float(h)/settings['txt_h_fits'])
    if scale < 1.0:
        return

    if text_type in ['light', 'stroke']:
        color = settings['light_color']
    else:
        color = settings['dark_color']

    draw_strk = lambda x, y: \
        cv2.putText(fr, x, y,
                    settings['font_face'],
                    scale,
                    settings['dark_color'],
                    settings['strk_thick'],
                    settings['font_type'])
    draw_text = lambda x, y: \
        cv2.putText(fr, x, y,
                    settings['font_face'],
                    scale,
                    color,
                    settings['txt_thick'],
                    settings['font_type'])

    txt = "butterflow {} ({})\n"\
          "Res: {},{}\n"\
          "Playback Rate: {:.2f} fps\n"
    txt = txt.format(__version__, sys.platform, w, h, rate)

    argspec = inspect.getargspec(flow_fn)
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
            if i == len(flow_kwargs)-1:
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
            draw_strk(line, origin)
        draw_text(line, origin)

    txt = "Region {}/{} F: [{}, {}] T: [{:.2f}s, {:.2f}s]\n"\
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
            draw_strk(line, origin)
        draw_text(line, origin)
