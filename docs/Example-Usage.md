# Example Usage

### Altering the frame rate (the global playback rate):

#### Examples:
1. Double a video's frame rate with `butterflow -r 2x <video>`.
    * `-r`, or `--playback-rate`, sets the global playback rate.
    * `-r 3x` would triple the frame rate, `-r 4x` would quadruple the frame rate, etc.
2. Set a video's frame rate to 60fps with `butterflow -r 60 <video>`.
3. Set a fractional frame rate: `butterflow -r 23.976 <video>`.
    * This command is the same as `butterflow -r 24/1.001 <video>`.

**Note:** In general frames will be interpolated if the frame rate is increased, otherwise they'll be dropped. The video's original rate will be used if `-r` is not set (an X fps input video will yield an X fps output video).

**Note:** BF isn't optimized for tasks that only involve dropping frames so use another tool like FFmpeg if that's the only thing you're doing.

### Altering speed, duration, and region fps:

#### Examples:
1. Set a video to 0.25x speed with `butterflow -s a=0,b=end,spd=0.25 <video>`.
    * `-s`, or `--subregions`, specifies a subregion to work on. Here the entire video is worked on.
    * `end` is a special keyword that signifies "to the end of the video".
    * `spd` is what we're targeting to alter in the region.
    * Since the playback rate is unchanged (`-r` is not set), this would produce a video with 4x frames. Original frames will be retained and interpolated frames will be inserted between them. Assuming the input video was a 1s 24fps video, this command would create a 4s output video with 96 total frames, 72 interpolated and 24 original.
2. Set a video's duration to be 8s long with `butterflow -s a=0,b=end,dur=8 <video>`.
3. Create 200 frames for every 1s of video with `butterflow -s a=0,b=end,fps=200 <video>`.
    * **Important:** `fps` is different from `-r`,  which sets the global playback rate.
    * Think of `fps` as "create `fps`=X frames for every 1 second in this region".

**Note:** In most cases slowing a video down or extending its duration will cause frames to be interpolated, otherwise they'll be dropped.

### Working on one region:

#### Examples:
1. Double the frame rate on a 1s region with `butterflow -r 2x -s a=1:30:24,b=1:30:25,spd=1 <video>`.
    * Setting `spd=1` has a nulling effect on the `-s` option. It means "work on this region but don't alter its speed, duration, or fps". It ensures that (1) only the `-r` option applies to the region and (2) only the `-r` argument will determine if frames will be dropped or rendered.
2. Slowmo a 1s region to 0.5x speed with `butterflow -s a=5,b=6,spd=0.5 <video>`.
3. Double the frame rate on a 1s region *and* slow it down: `butterflow -r 2x -s a=0,b=1,spd=0.5x <video>`.
    * Assume the video's original frame rate was 24fps. This command would create an output video with 24\*2\*2 frames because `-r` and `spd=<lower>` is being used together.
4. Work on the whole video (the entire region) with `butterflow -s a=0,b=end,spd=0.9`.

**Tip:** The `-k`, or `--keep-subregions`, option will render regions that are not explicitly specified into the output video at 1x speed (the playback rate still applies across these regions).

**Tip:** Rendering will be faster if you're working on smaller regions. Use `-s` on a small segment of a video to test out settings before working on a larger one. Scaling the video down with `-vs <scale from 0-1.0>` is another way to speed up rendering.

### Multiple regions:
Separate regions with a colon `:`.

#### Examples:
1. With two regions: `butterflow -s a=1,b=2,spd=0.5:a=9,b=end,spd=0.5 <video>`.
2. With 4 regions: `butterflow -s a=0,b=6,spd=0.125:a=6,b=6.8,dur=3:a=6.8,b=7,dur=0.4:a=20,b=end,fps=200 <video>`.

## Robustness of image
BF uses the Farneback algorithm to compute dense optical flows for frame interpolation. You can pass in different values to the function to fine-tune the quality (robustness of image) of the resulting videos.

### Tips and strategies

#### Optimal input videos:
BF works best on input videos with an inherent "fluidity" to them, videos where moving elements in a scene have a steady and traceable trail of motion.

#### Artifact-less frames are a priority:
Use the `-sm` flag if having artifact-less frames is a priority. This will tune settings to emphasize blending frames over the default behavior of warping pixels.

However, one drawback of using a blend as the primary effect is that ghosting will be more apparent when the motion between frames is large. Don't set this flag if you only intend to do simple frame rate increases, as long as the target rate isn't a lot higher than the original frame rate (e.g., `-r <2x to 3x, or not too large of a rate differential>`), because you would lose the "soap opera effect" quality that the default settings provide, unless having a clean effect with minimal warping and artifacts is necessary.

#### Need to blend more or warp more?
Tune the `--poly-s` setting. `--poly-s=<lower>` will blend more, `--poly-s=<higher>` will warp more.

#### Few source frames to work with/time-lapse videos:
These types of videos aren't optimal for usage with BF because the motion between frames tends to be too extreme. If pure blending with the `-sm` isn't providing the effect you're looking for (you need motion interpolation), then you can counteract the lack of frames by rendering tons of interpolated frames at first (typically with `-r <higher>`, `spd=<very low>` or `fps=<higher>`, or a combination thereof), and then speeding up the playback to a desired speed.

For example `butterflow -v -r24 -s a=0,b=3.9,spd=.1 --poly-s=0.8 <input video> -o <temp video>`, followed by `butterflow -v -s full,spd=1.5 <temp video> -o <output video>`.

#### Artifacts and obfuscating them:
The presence of pixel artifacts/undesirable warping effects depends on many factors: the frame rate of the source video, its dimensions, the original image quality, and the type of motion present. Artifacts will be more prevalent when the motion between source frames is atypical or falls on extremes (e.g., during scene changes, camera shot changes, when people or objects pop in and out between frames or cover large distances in a short period of time).

Lower resolution videos are good at obfuscating artifacts and they tend to be less prone to producing them. If the output image is artifact heavy, try scaling the video down with `-vs <lower>`.

You can skip over scene/camera shot changes with the `-s` option.

#### Output video is stuttering?
Duplicate frames will cause the output video to stutter when doing slowmo. Try using FFmpeg's decimate filter to generate a readout of what frames the filter thinks are duplicates and then remove them before passing the video to BF.

If you're not using slow motion check if there is stuttering in the input video itself.
