# Example Usage
Run `butterflow -h` for a full list of options and their default values.

## Typical commands that you will use
### Frame interpolation
Double the frame rate:

```
butterflow -r 2x [video]
```

Set a video's frame rate to 96fps:

```
butterflow -r 96 [video]
```

Use the `-sm`, `--smooth-motion` flag if having artifact-less frames is a
priority. This will tune settings to emphasize blending frames over warping
pixels, which is the default behavior.

### Altering speed and duration
Slow-mo a video to 0.25x speed:

```
butterflow -s full,spd=0.25 [video]
```

Set a video's duration to be 30s long:

```
butterflow -s full,dur=30 [video]
```

This will speed up or slow down the video depending on it's original duration.

### Working on one region
Slow-mo a 1s region to 0.5x speed:

```
butterflow -t -s a=5,b=6,spd=0.5 [video]
```

The `-t`, `--trim-regions` option will discard all regions that are not
explicitly specified. Keep in mind, rendering will be faster if you're working
on smaller regions, so this flag will be useful if you need to do quick tests.

### Multiple regions
Separate regions with a colon `:`.

With two regions:

```
butterflow -t -s a=1,b=2,spd=0.5:a=9,b=end,spd=0.5 [video]
```

With four regions:

```
butterflow -t -s \
a=0,b=6,spd=0.125:\
a=6,b=6.8,dur=3:\
a=6.8,b=7,dur=0.4:\
a=20,b=end,fps=200 [video]
```

## Using fractions
You can use fractions for rates, e.g., `30/1.001` is equivalent to 29.97fps.

## Robustness of image
Butterflow uses the Farneback algorithm to compute dense optical flows for frame
interpolation. You can pass in different values to the function to fine-tune the
quality (robustness of image) of the resulting videos.

Run `butterflow -h` for a list of advanced options and their default values.
