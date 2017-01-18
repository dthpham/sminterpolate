# Example Usage
**Tip:** Run `butterflow -h` for a full list of options and their default values.

### Altering the frame rate (the global playback rate):
#### Examples:
1. Double a video's frame rate with `butterflow -r 2x <video>`.
 * `-r`, or `--playback-rate`, sets the global playback rate.
 * `-r 3x` would triple the frame rate, and `-r 4x` would quadruple the frame rate, etc.
2. Set a video's frame rate to 60fps with `butterflow -r 60 <video>`.
3. Set a fractional frame rate: `butterflow -r 23.976 <video>`.
 * This command is the same as `butterflow -r 24/1.001 <video>`.

**Note:** In general, frames will be interpolated if the frame rate is increased, otherwise they will be dropped. If `-r` is not set, the video's original rate will be used (a 24fps input video will yield a 24fps output video, etc.).

**Tip:** BF is not optimized for tasks that only involve dropping frames, so use another tool like FFMPEG if that's the only thing you're doing.

### Altering speed, duration, and region fps:
#### Examples:
1. Set a video to 0.25x speed with `butterflow -s a=0,b=end,spd=0.25 <video>`.
 * `-s` specifies a subregion to work on. The entire video is being worked on in this case.
 * `end` is a special keyword that signifies "to the end of the video".
 * `spd` is what we're targeting in the region.
 * Since the playback rate is unchanged (`-r` is not set) this would produce a video with 4x more frames, all interpolated.
2. Set a video's duration to be 8s long with `butterflow -s a=0,b=end,dur=8 <video>`.
3. Create 200 frames for every 1s of video with `butterflow -s a=0,b=end,fps=200 <video>`.
 * `fps` is different from `-r`, which sets the global playback rate.

**Note:** In most cases, slowing a video down or extending its duration will cause frames to be interpolated, otherwise they will be dropped.

### Working on one region:
#### Examples:
1. Double the frame rate on a 1s region with `butterflow -r 2x -s a=1:30:24,b=1:30:25,spd=1 <video>`.
 * Setting `spd=1` has a nulling effect on the `-s` option, it ensures that only the `-r` option will determine if frames will be dropped or rendered.
2. Slowmo a 1s region to 0.5x speed with `butterflow -s a=5,b=6,spd=0.5 <video>`.
3. Double the frame rate on a 1s region *and* slow it down: `butterflow -r 2x -s a=0,b=1,spd=0.5x <video>`.
 * Assume the video's original frame rate was 24fps. This command would create an output video with 24\*2\*2 frames because `-r` and `spd=<lower>` is being used in conjunction.
4. Work on the whole video (the entire region) with `butterflow -s a=0,b=end,spd=0.9`.
 * This command is the same as `butterflow -s full,spd=0.9`.

**Tip:** The `-k` option will render regions that are not explicitly specified into the output video at 1x speed (the playback rate still applies across these regions).

**Tip:** Rendering will be faster if you're working on smaller regions so use `-s` on small segments of a video when you need to do quick tests. Scaling the video down with `-vs <scale from 0-1.0>` is another way to speed up rendering.

### Multiple regions:
Separate regions with a colon `:`.

#### Examples:
1. With two regions: `butterflow -s a=1,b=2,spd=0.5:a=9,b=end,spd=0.5 <video>`.
2. With 4 regions: `butterflow -s a=0,b=6,spd=0.125:a=6,b=6.8,dur=3:a=6.8,b=7,dur=0.4:a=20,b=end,fps=200 <video>`.

## Robustness of image:
BF uses the Farneback algorithm to compute dense optical flows for frame interpolation. You can pass in different values to the function to fine-tune the quality (robustness of image) of the resulting videos.

**Tip:** BF's slow motion feature works best on input videos with an inherent "fluidity" to them, videos where moving elements in a scene have a steady and traceable trail of motion.

**Tip:** The presence of artifacts depends on many factors, which includes  the frame rate of the source video, its dimensions, original image quality, and the type of motion present. Pixel artifacts will be more prevalent when the motion between source frames is atypical or fall on extremes (e.g., during scene changes, when people or objects pop in and out or cover large distances in a short period of time).

You can minimize the negative effects of large motion by rendering more frames, typically done with `-r <higher>`, `fps=<higher>` or `spd=<very low>`, or a combination thereof. Lower resolution videos are good at obfuscating artifacts and they tend to be less prone to producing them. So if the output image is artifact heavy, try scaling the video down with `-vs <lower>`. You can skip over scene changes with the `-s` option.

**Tip:** Use the `-sm` flag if having artifact-less frames is a priority. This will tune settings to emphasize blending frames over the default behavior of warping pixels.

However, one drawback of using a blend as the primary effect is that ghosting will be more apparent when the motion between frames is large. Don't set this flag if you only intend to do simple frame rate increases, as long as the target rate isn't a lot higher than the original frame rate (e.g., `-r <2x to 3x, not too large of a rate>`), because you would lose the "soap opera effect" quality that the default settings provide, unless having a clean effect with minimal warping and artifacts is necessary.
