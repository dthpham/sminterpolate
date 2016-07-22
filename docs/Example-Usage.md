# Example Usage
**Tip:** Run `butterflow -h` for a full list of options and their default values.

## Typical commands that will be used

### Altering the frame rate:
#### Examples:
* Double a video's frame rate with `butterflow -r 2x <VIDEO>`.
 * `-r` sets the playback rate and will still apply across all subregions even if you use `-s`.
 * `3x` would triple the frame rate, etc.
* Set a video's frame rate to 60fps with `butterflow -r 60 <VIDEO>`.
* Set a frame rate with fractions: `butterflow -r 24/1.001 <VIDEO>`.
 * This is equivalent to using 23.976.

In general, frames will be interpolated if the rate is increased, otherwise they will be dropped.

### Altering speed and duration:
#### Examples:
* Set a video to 0.25x speed with `butterflow -s full,spd=0.25 <VIDEO>`.
 * `-s` specifies a subregion to work on.
 * `full` is a special keyword that tells butterflow to work on the entire video.
 * `spd` is what we're targeting in the region.
 * Since the frame rate is unchanged, this would produce a video with 4x more frames, all interpolated.
* Set a video's duration to be 8s long with `butterflow -s full,dur=8 <VIDEO>`.
* Create 200 frames for every 1s of video with `butterflow -s full,fps=200 <VIDEO>`.
 * `fps` is different from `-r`, which sets the overall playback rate.

In most cases, slowing a video down/extending it's duration will cause frames to be interpolated, otherwise they will be dropped.

### Working on one region:
#### Examples:
* Double the frame rate on a 1s region with `butterflow -r 2x -s a=1:30:24,b=1:30:25,spd=1 <VIDEO>`.
 * Setting `spd=1` will not alter the video's speed.
* Slowmo a 1s region to 0.5x speed with `butterflow -s a=5,b=6,spd=0.5 <VIDEO>`.
* Double the frame rate on a 1s region *and* slow it down: `butterflow -r 2x -s a=0,b=1,spd=0.5x <VIDEO>`.
 * Assume the video's original frame rate was 24fps. This command would create an output video with 24\*2\*2 frames.
* Work on the whole video (the entire region) with `butterflow -s a=0,b=end,spd=0.9`.
 * The `end` keyword signifies "to the end of the video".
 * This command is the same as `butterflow -s full,spd=0.9`.

**Tip:** Rendering will be faster if you're working on smaller regions so use `-s` on small segments of a video if you need to do quick tests. Scaling the video down with `-vs` is another way to speed up rendering.

**Tip:** The `-k` option will render regions that are not explicitly specified into the output video at 1x speed (the playback rate still applies across these regions).

### Multiple regions:
Separate regions with a colon `:`.

#### Examples:
* With two regions: `butterflow -s a=1,b=2,spd=0.5:a=9,b=end,spd=0.5 <VIDEO>`.
* With 4 regions: `butterflow -s a=0,b=6,spd=0.125:a=6,b=6.8,dur=3:a=6.8,b=7,dur=0.4:a=20,b=end,fps=200 <VIDEO>`.

## Robustness of image
Butterflow uses the Farneback algorithm to compute dense optical flows for frame interpolation. You can pass in different values to the function to fine-tune the quality (robustness of image) of the resulting videos.

**Tip:** Use the `-sm` flag if having artifact-less frames is a priority. This will tune settings to emphasize blending frames over the default behavior of warping pixels.
