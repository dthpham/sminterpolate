import unittest
from butterflow.cli import time_string_to_ms, parse_tval_string, \
    subregion_from_string, subregion_from_string_full_key, \
    subregion_from_string_end_key, sequence_from_string
from butterflow.sequence import RenderSubregion


class CliUtilTestCase(unittest.TestCase):
    def test_parse_tval_string_fps(self):
        t,v = parse_tval_string('fps=0')
        self.assertEqual(t,'fps')
        self.assertEqual(v,0)
        t,v = parse_tval_string('fps=30')
        self.assertEqual(t,'fps')
        self.assertEqual(v,30)
        t,v = parse_tval_string('fps=59.94')
        self.assertEqual(t,'fps')
        self.assertEqual(v,59.94)

    def test_parse_tval_string_fps_fraction(self):
        t,v = parse_tval_string('fps=24000/1001')
        self.assertEqual(t,'fps')
        self.assertEqual(v,24000.0/1001)
        t,v = parse_tval_string('fps=24/1.001')
        self.assertEqual(t,'fps')
        self.assertEqual(v,24/1.001)
        t,v = parse_tval_string('fps=24.0/1.001')
        self.assertEqual(t,'fps')
        self.assertEqual(v,24/1.001)

    def test_parse_tval_string_dur(self):
        t,v = parse_tval_string('dur=0')
        self.assertEqual(t,'dur')
        self.assertEqual(v,0.0)
        t,v = parse_tval_string('dur=1')
        self.assertEqual(t,'dur')
        self.assertEqual(v,1000.0)
        t,v = parse_tval_string('dur=1.1')
        self.assertEqual(t,'dur')
        self.assertEqual(v,1100.0)

    def test_parse_tval_string_spd(self):
        t,v = parse_tval_string('spd=0')
        self.assertEqual(t,'spd')
        self.assertEqual(v,0.0)
        t,v = parse_tval_string('spd=1')
        self.assertEqual(t,'spd')
        self.assertEqual(v,1.0)
        t,v = parse_tval_string('spd=0.5')
        self.assertEqual(t,'spd')
        self.assertEqual(v,0.5)

    def test_parse_tval_string_invalid(self):
        with self.assertRaises(ValueError):
            parse_tval_string('dne=1')
        with self.assertRaises(ValueError):
            parse_tval_string('fps=a')
        with self.assertRaises(ValueError):
            parse_tval_string('dur=a')
        with self.assertRaises(ValueError):
            parse_tval_string('spd=a')

    def test_subregion_from_string_fps(self):
        s = subregion_from_string(
            'a=00:05:00.0,b=00:05:30.0,fps=59.94')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,(5*60)*1000)
        self.assertEqual(s.tb,(5*60+30)*1000)
        self.assertEqual(s.fps,59.94)

    def test_subregion_from_string_fps_fraction(self):
        s = subregion_from_string(
            'a=00:00:00.5,b=00:00:01.0,fps=24000/1001')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,0.5*1000)
        self.assertEqual(s.tb,1.0*1000)
        self.assertEqual(s.fps,24000.0/1001)

    def test_subregion_from_string_fps_fraction_with_decimal(self):
        s = subregion_from_string(
            'a=00:00:00.5,b=00:00:01.0,fps=24/1.001')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,0.5*1000)
        self.assertEqual(s.tb,1.0*1000)
        self.assertEqual(s.fps,24/1.001)

    def test_subregion_from_string_duration(self):
        s = subregion_from_string(
            'a=01:20:31.59,b=01:21:34.0,dur=3')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,(1*3600+20*60+31.59)*1000)
        self.assertEqual(s.tb,(1*3600+21*60+34.0)*1000)
        self.assertEqual(s.dur,3*1000)

    def test_subregion_from_string_speed(self):
        s = subregion_from_string(
            'a=00:00:01.0,b=00:00:02.0,spd=0.5')
        self.assertIsInstance(s, RenderSubregion)
        self.assertEqual(s.ta,1*1000)
        self.assertEqual(s.tb,2*1000)
        self.assertEqual(s.spd,0.5)

    def test_subregion_from_string_full_key(self):
        s = subregion_from_string_full_key(
            'full,fps=48', 60*1000)
        self.assertEqual(s.ta,0)
        self.assertEqual(s.tb,60*1000)
        self.assertEqual(s.fps,48)

    def test_subregion_from_string_end_key(self):
        s = subregion_from_string_end_key(
            'a=1.0,b=end,dur=20', 30*1000)
        self.assertEqual(s.ta,1*1000)
        self.assertEqual(s.tb,30*1000)
        self.assertEqual(s.dur,20*1000)

    def test_sequence_from_string(self):
        vs = sequence_from_string(5*1000,5*24,
            'a=00:00:00.5,b=00:00:01.2,fps=48;'
            'a=00:00:01.3,b=00:00:01.5,fps=60/1.001;'
            'a=00:00:02.3,b=00:00:03.3,fps=24000/1001;'
            'a=00:00:03.3,b=00:00:04.3,spd=0.25;'
            'a=00:00:04.3,b=00:00:04.999,dur=5')
        self.assertEqual(len(vs.subregions), 5)
        vs = sequence_from_string(5*1000,5*24,
            'a=00:00:01.0,b=end,fps=400')
        self.assertEqual(len(vs.subregions), 1)
        vs = sequence_from_string(5*1000,5*24,
            'full,spd=0.125')
        self.assertEqual(len(vs.subregions), 1)
        vs = sequence_from_string(1*1000,5*24,
            'a=00:00:00.0,b=00:00:01.0,fps=1;'
            'a=00:00:01.0,b=end,fps=1')
        self.assertEqual(len(vs.subregions), 2)

    def test_sequence_from_string_full_fails(self):
        with self.assertRaises(RuntimeError):
            vs = sequence_from_string(5*1000,5*24,
                'full,fps=48;'
                'a=00:00:02.3,b=00:00:03.3,fps=24000/1001')
        with self.assertRaises(RuntimeError):
            vs = sequence_from_string(5*1000,5*24,
                'full,fps=400;'
                'full,spd=0.5')

    def test_sequence_from_string_end_fails(self):
        with self.assertRaises(ValueError):
            vs = sequence_from_string(5*1000,5*24,
                'a=end,b=00:00:01.0,fps=1')
        with self.assertRaises(RuntimeError):
            vs = sequence_from_string(5*1000,5*24,
                'a=1,b=end,fps=400;'
                'a=2,b=end,spd=0.5')
        with self.assertRaises(RuntimeError):
            vs = sequence_from_string(5*1000,5*24,
                'a=end,b=end,fps=1;'
                'a=end,b=end,fps=1')

    def test_sequence_from_string_none_return_none(self):
        vs = sequence_from_string(1,1,None)
        self.assertIsNotNone(vs)

    def test_time_string_to_ms_subsecond(self):
        self.assertEqual(time_string_to_ms('.001'),1)
        self.assertEqual(time_string_to_ms('.010'),10)
        self.assertEqual(time_string_to_ms('.100'),100)

    def test_time_string_to_ms_seconds(self):
        self.assertEqual(time_string_to_ms('1.1'),1.1*1000)
        self.assertEqual(time_string_to_ms('1.01'),1.01*1000)
        self.assertEqual(time_string_to_ms('1.001'),1.001*1000)
        self.assertEqual(time_string_to_ms('1'),1*1000)
        self.assertEqual(time_string_to_ms('01'),1*1000)
        self.assertEqual(time_string_to_ms('001'),1*1000)
        self.assertEqual(time_string_to_ms('30'),30*1000)
        self.assertEqual(time_string_to_ms('90'),90*1000)
        self.assertEqual(time_string_to_ms('100'),100*1000)

    def test_time_string_to_ms_minutes(self):
        self.assertEqual(time_string_to_ms('1:00'),1*60*1000)
        self.assertEqual(time_string_to_ms('01:00'),1*60*1000)
        self.assertEqual(time_string_to_ms('00:34'),34*1000)
        self.assertEqual(time_string_to_ms('12:34'),(12*60+34)*1000)
        self.assertEqual(time_string_to_ms('123:45'),(123*60+45)*1000)

    def test_time_string_to_ms_hours(self):
        self.assertEqual(time_string_to_ms('1:23:45'),
                                           (1*3600+23*60+45)*1000)
        self.assertEqual(time_string_to_ms('0:23:45'),
                                           (0*3600+23*60+45)*1000)

    def test_time_string_to_ms_explicit(self):
        self.assertEqual(time_string_to_ms('00:00:00.001'),1)
        self.assertEqual(time_string_to_ms('00:00:00.100'),100)
        self.assertEqual(time_string_to_ms('00:17:33.090'),
                                           (0*3600+17*60+33.09)*1000)
        self.assertEqual(time_string_to_ms('01:30:59.100'),
                                           (1*3600+30*60+59.1)*1000)
        self.assertEqual(time_string_to_ms('02:09:00.123'),
                                           (2*3600+9*60+0.123)*1000)

    def test_time_string_to_ms_fails(self):
        with self.assertRaises(ValueError):
            time_string_to_ms('')
        with self.assertRaises(ValueError):
            time_string_to_ms('a')
        with self.assertRaises(ValueError):
            time_string_to_ms('00:00:0:00.00a')
        with self.assertRaises(ValueError):
            time_string_to_ms('00:00:00:00.000')


if __name__ == '__main__':
    unittest.main()
