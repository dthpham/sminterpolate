# Example Usage
**Tip** Run `butterflow -h` for a full list of options and their default values.

## Typical commands that you'll use
### Altering frame rate
Double the frame rate:
```
butterflow -r 2x [video]
```

Set a video's frame rate to 96fps:
```
butterflow -r 96 [video]
```

These commands will remove frames or interpolate new ones based on several
factors, but in general frames will be interpolated if the rate is
increased otherwise they will be dropped.

Use the `-sm`, `--smooth-motion` flag if having artifact-less frames is a
priority. This will tune settings to emphasize blending frames over the default
behavior of warping pixels.

### Altering speed and duration
Set video to 0.25x speed:
```
butterflow -s full,spd=0.25 [video]
```

Set a video's duration to be 30s long:
```
butterflow -s full,dur=30 [video]
```

In most cases, slowing a video down or extending it's duration will cause frames
to be interpolated otherwise they will be dropped.

### Working on one region
Double the frame rate on a 1s region:
```
butterflow -r 2x -s a=1:30:24,b=1:30:25,spd=1
```

Slow-mo a 1s region to 0.5x speed:
```
butterflow -s a=5,b=6,spd=0.5 [video]
```

Rendering will be faster if you're working on smaller regions so use `-s` on
small segments of a video if you need to do quick tests.

The `-k`, `--keep-regions` option will render regions that are not explicitly
specified into the output video.

### Multiple regions
Separate regions with a colon `:`.

With two regions:
```
butterflow -s a=1,b=2,spd=0.5:a=9,b=end,spd=0.5 [video]
```

With four regions:
```
butterflow -s \
a=0,b=6,spd=0.125:\
a=6,b=6.8,dur=3:\
a=6.8,b=7,dur=0.4:\
a=20,b=end,fps=200 [video]
```

## Flexible time syntax
Valid time inputs include [hr:min:sec], [min:sec], [sec], [sec.xxx].

## Fractions for rates
You can use fractions for rates, e.g., 30/1.001 is equivalent to 29.97fps.

## Robustness of image
Butterflow uses the Farneback algorithm to compute dense optical flows for frame
interpolation. You can pass in different values to the function to fine-tune the
quality (robustness of image) of the resulting videos.

Run `butterflow -h` for a list of advanced options and their default values.
