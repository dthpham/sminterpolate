import unittest
from butterflow.cli import w_h_from_str, rate_from_str, time_str_to_ms, \
    parse_tval_str, sub_from_str, sub_from_str_full_key, \
    sub_from_str_end_key, sequence_from_str
from butterflow.sequence import RenderSubregion


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.t_val_targets = [
            'spd',
            'dur',
            'fps']

    def test_w_h_from_str_diff_w_and_h(self):
        w, h = w_h_from_str('854:480', 640, 360)
        self.assertTupleEqual((w, h), (854, 480))

    def test_w_h_from_str_w_by_h_keep_aspect(self):
        w, h = w_h_from_str('640:-1', 960, 518)
        self.assertTupleEqual((w, h), (640, 344))
        w, h = w_h_from_str('640:-1', 640, 360)
        self.assertTupleEqual((w, h), (640, 360))
        w, h = w_h_from_str('-1:360', 640, 360)
        self.assertTupleEqual((w, h), (640, 360))
        w, h = w_h_from_str('1280:-1', 640, 360)
        self.assertTupleEqual((w, h), (1280, 360*2))
        w, h = w_h_from_str('-1:720', 640, 360)
        self.assertTupleEqual((w, h), (640*2, 720))
        w, h = w_h_from_str('320:-1', 640, 360)
        self.assertTupleEqual((w, h), (320, 360*0.5))
        w, h = w_h_from_str('-1:180', 640, 360)
        self.assertTupleEqual((w, h), (640*0.5, 180))

    def test_w_h_from_str_w_by_h_both_negative_one(self):
        w, h = w_h_from_str('-1:-1', 640, 360)
        self.assertTupleEqual((w, h), (640, 360))

    def test_w_h_from_str_factor(self):
        w, h = w_h_from_str('1', 640, 360)
        self.assertTupleEqual((w, h), (640, 360))
        w, h = w_h_from_str('1.1', 640, 360)
        self.assertTupleEqual((w, h), (int(640*1.1), int(360*1.1)))
        w, h = w_h_from_str('0.9', 640, 360)
        self.assertTupleEqual((w, h), (int(640*0.9), int(360*0.9)))

    def test_w_h_from_str_divisible_by_two_fails(self):
        with self.assertRaises(ValueError):
            w_h_from_str('640:1', 640, 360)
        with self.assertRaises(ValueError):
            w_h_from_str('1:360', 640, 360)

    def test_w_h_from_str_unknown_char_fails(self):
        with self.assertRaises(ValueError):
            w_h_from_str('unknown:360', 640, 360)

    def test_w_h_from_str_unknown_negative_number_fails(self):
        with self.assertRaises(ValueError):
            w_h_from_str('-2:360', 640, 360)

    def test_rate_from_str_is_none(self):
        self.assertEqual(rate_from_str(None, 30), 30)

    def test_rate_from_str_integer_or_float(self):
        self.assertEqual(rate_from_str('24', 30), 24)
        self.assertEqual(rate_from_str('25.0', 30), 25)

    def test_rate_from_str_fractional(self):
        self.assertEqual(rate_from_str('24000/1001', 30), 24000*1.0/1001)

    def test_rate_from_str_non_rational_fraction(self):
        self.assertEqual(rate_from_str('24.0/1001', 30), 24*1.0/1001)
        self.assertEqual(rate_from_str('24/1.001', 30), 24*1.0/1.001)
        self.assertEqual(rate_from_str('24.0/1.001', 30), 24*1.0/1.001)

    def test_rate_from_str_multiple_of(self):
        self.assertEqual(rate_from_str('1x', 23.976), 23.976)
        self.assertEqual(rate_from_str('1.1x', 23.976), 23.976*1.1)
        self.assertEqual(rate_from_str('0.9x', 23.976), 23.976*0.9)

    def test_rate_from_str_less_than_equal_to_zero_fails(self):
        with self.assertRaises(ValueError):
            rate_from_str('0', 30)
        with self.assertRaises(ValueError):
            rate_from_str('-1', 30)

    def test_rate_from_str_unknown_char_fails(self):
        with self.assertRaises(ValueError):
            rate_from_str('unknown', 30)

    def test_time_str_to_ms_ms(self):
        self.assertEqual(time_str_to_ms('.000'), 0)
        self.assertEqual(time_str_to_ms('.111'), 111)

    def test_time_str_to_ms_sec(self):
        self.assertEqual(time_str_to_ms('0'), 0)
        self.assertEqual(time_str_to_ms('1'), 1*1000)
        self.assertEqual(time_str_to_ms('00'), 0)
        self.assertEqual(time_str_to_ms('01'), 1*1000)
        self.assertEqual(time_str_to_ms('10'), 10*1000)

    def test_time_str_to_ms_sec_and_ms_precision(self):
        self.assertEqual(time_str_to_ms('0.0'), 0)
        self.assertEqual(time_str_to_ms('0.1'), 100)
        self.assertEqual(time_str_to_ms('1.0'), 1*1000)
        self.assertEqual(time_str_to_ms('1.1'), 1*1000+100)

    def test_time_str_to_ms_min(self):
        self.assertEqual(time_str_to_ms('0:00'), 0)
        self.assertEqual(time_str_to_ms('1:00'), 1*60*1000)
        self.assertEqual(time_str_to_ms('00:00'), 0)
        self.assertEqual(time_str_to_ms('01:00'), 1*60*1000)
        self.assertEqual(time_str_to_ms('10:00'), 10*60*1000)

    def test_time_str_to_ms_hrs(self):
        self.assertEqual(time_str_to_ms('0:00:00'), 0)
        self.assertEqual(time_str_to_ms('1:00:00'), 1*3600*1000)
        self.assertEqual(time_str_to_ms('00:00:00'), 0)
        self.assertEqual(time_str_to_ms('01:00:00'), 1*3600*1000)
        self.assertEqual(time_str_to_ms('10:00:00'), 10*3600*1000)

    def test_time_str_to_ms_min_and_sec_no_pad_zero(self):
        self.assertEqual(time_str_to_ms('0:0'), 0)
        self.assertEqual(time_str_to_ms('0:1'), 1*1000)
        self.assertEqual(time_str_to_ms('1:0'), 1*60*1000)
        self.assertEqual(time_str_to_ms('1:1'), 1*60*1000+1*1000)

    def test_time_str_to_ms_hrs_and_min_no_pad_zero(self):
        self.assertEqual(time_str_to_ms('0:0:00'), 0)
        self.assertEqual(time_str_to_ms('0:1:00'), 1*60*1000)
        self.assertEqual(time_str_to_ms('1:0:00'), 1*3600*1000)
        self.assertEqual(time_str_to_ms('1:1:00'), 1*3600*1000+1*60*1000)

    def test_time_str_to_ms_fails(self):
        with self.assertRaises(ValueError):
            time_str_to_ms('')
        with self.assertRaises(ValueError):
            time_str_to_ms('00:00:0unknown')
        with self.assertRaises(ValueError):
            time_str_to_ms('00:00:00:00.000')

    def test_parse_tval_str_get_target(self):
        for t in self.t_val_targets:
            self.assertEqual(parse_tval_str('{}=1'.format(t))[0], t)

    def test_parse_tval_str_get_value(self):
        for t in self.t_val_targets:
            for v in [1, 1.1, 0.9]:
                _, parsed_value = parse_tval_str('{}={}'.format(t, v))
                if t == 'dur':
                    v *= 1000.0
                self.assertEqual(parsed_value, v)

    def test_parse_tval_str_value_is_float(self):
        for t in self.t_val_targets:
            self.assertIsInstance(parse_tval_str('{}=1'.format(t))[1], float)

    def test_parse_tval_str_fps_fraction(self):
        self.assertEqual(parse_tval_str('fps=24/1001')[1], 24.0/1001)

    def test_parse_tval_str_fps_non_rational_fraction(self):
        for x in ['24/1.001', '24.0/1.001']:
            self.assertEqual(parse_tval_str('fps={value}'.format(
                value=x
            ))[1], 24.0/1.001)
        self.assertEqual(parse_tval_str('fps=24.0/1001')[1], 24.0/1001)

    def test_parse_tval_str_target_dne_fails(self):
        with self.assertRaises(ValueError):
            parse_tval_str('does_not_exist=1')

    def test_parse_tval_str_value_not_a_number_fails(self):
        for t in self.t_val_targets:
            with self.assertRaises(ValueError):
                parse_tval_str('{target}=not_a_number'.format(target=t))

    def test_sub_from_str_fps(self):
        s = sub_from_str(
            'a=00:05:00.0,b=00:05:30.0,fps=59.94')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,(5*60)*1000)
        self.assertEqual(s.tb,(5*60+30)*1000)
        self.assertEqual(s.fps,59.94)

    def test_sub_from_str_fraction(self):
        s = sub_from_str(
            'a=00:00:00.5,b=00:00:01.0,fps=24000/1001')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,0.5*1000)
        self.assertEqual(s.tb,1.0*1000)
        self.assertEqual(s.fps,24000.0/1001)

    def test_sub_from_str_non_rational_fraction(self):
        s = sub_from_str(
            'a=00:00:00.5,b=00:00:01.0,fps=24/1.001')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,0.5*1000)
        self.assertEqual(s.tb,1.0*1000)
        self.assertEqual(s.fps,24/1.001)

    def test_sub_from_str_dur(self):
        s = sub_from_str(
            'a=01:20:31.59,b=01:21:34.0,dur=3')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,(1*3600+20*60+31.59)*1000)
        self.assertEqual(s.tb,(1*3600+21*60+34.0)*1000)
        self.assertEqual(s.dur,3*1000)

    def test_sub_from_str_spd(self):
        s = sub_from_str(
            'a=00:00:01.0,b=00:00:02.0,spd=0.5')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,1*1000)
        self.assertEqual(s.tb,2*1000)
        self.assertEqual(s.spd,0.5)

    def test_sub_from_str_time_a_greater_than_time_b_fails(self):
        with self.assertRaises(ValueError):
            s = sub_from_str(
                'a=00:00:02.0,b=00:00:01.0,spd=2')

    def test_sub_from_str_full_key(self):
        s = sub_from_str_full_key(
            'full,fps=48', 60*1000)
        self.assertEqual(s.ta,0)
        self.assertEqual(s.tb,60*1000)
        self.assertEqual(s.fps,48)

    def test_sub_from_str_full_key_fails(self):
        with self.assertRaises(ValueError):
            vs = sequence_from_str(5*1000,5*24,
                'a=end,b=00:00:01.0,fps=1')
        with self.assertRaises(RuntimeError):
            vs = sequence_from_str(5*1000,5*24,
                'a=1,b=end,fps=400:'
                'a=2,b=end,spd=0.5')
        with self.assertRaises(RuntimeError):
            vs = sequence_from_str(5*1000,5*24,
                'a=end,b=end,fps=1:'
                'a=end,b=end,fps=1')

    def test_sub_from_str_end_key(self):
        s = sub_from_str_end_key(
            'a=1.0,b=end,dur=20', 30*1000)
        self.assertEqual(s.ta,1*1000)
        self.assertEqual(s.tb,30*1000)
        self.assertEqual(s.dur,20*1000)

    def test_sub_from_str_end_key_fails(self):
        with self.assertRaises(ValueError):
            vs = sequence_from_str(5*1000,5*24,
                'full,fps=48:'
                'a=00:00:02.3,b=00:00:03.3,fps=24000/1001')
        with self.assertRaises(ValueError):
            vs = sequence_from_str(5*1000,5*24,
                'full,fps=400:'
                'full,spd=0.5')

    def test_sequence_from_str_is_none(self):
        vs = sequence_from_str(1,30,None)
        self.assertEqual(len(vs.subregions), 0)

    def test_sequence_from_str_general(self):
        vs = sequence_from_str(5*1000,5*24,
            'a=00:00:00.5,b=00:00:01.2,fps=48:'
            'a=00:00:01.3,b=00:00:01.5,fps=60/1.001:'
            'a=00:00:02.3,b=00:00:03.3,fps=24000/1001:'
            'a=00:00:03.3,b=00:00:04.3,spd=0.25:'
            'a=00:00:04.3,b=00:00:04.999,dur=5')
        self.assertEqual(len(vs.subregions), 5)
        vs = sequence_from_str(5*1000,5*24,
            'a=00:00:01.0,b=end,fps=400')
        self.assertEqual(len(vs.subregions), 1)
        vs = sequence_from_str(5*1000,5*24,
            'full,spd=0.125')
        self.assertEqual(len(vs.subregions), 1)
        vs = sequence_from_str(1*1000,5*24,
            'a=00:00:00.0,b=00:00:01.0,fps=1:'
            'a=00:00:01.0,b=end,fps=1')
        self.assertEqual(len(vs.subregions), 2)

    def test_sequence_from_str_bad_separator(self):
        with self.assertRaises(ValueError):
            sequence_from_str(5*1000,5*24,
                'a=00:00:00.1,b=00:00:00.1,fps=48,'
                'a=00:00:00.1,b=00:00:00.2,fps=60/1.001')
        with self.assertRaises(ValueError):
            sequence_from_str(5*1000,5*24,
                'a=00:00:00.1,b=00:00:00.1,fps=48+'
                'a=00:00:00.1,b=00:00:00.2,fps=60/1.001')

if __name__ == '__main__':
    unittest.main()
