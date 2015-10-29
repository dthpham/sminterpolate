# Example Usage
Run `butterflow -h` for a full list of options and their default values.

## Interpolation
Double the frame rate:

```
butterflow -sm -r 2x [video]
```

Increase a video's frame rate to 96fps:

```
butterflow -sm -r 96 [video]
```

## Slow motion
Slow-mo a video to 0.25x speed:

```
butterflow -s full,spd=0.25 [video]
```

Slow-mo a video to be 30s long:

```
butterflow -s full,dur=30 [video]
```

## Working on a single region
Slow-mo a 1s region by 0.5x speed:

```
butterflow -s a=5,b=6,spd=0.5 [video]
```

Slowmo a 0.5s region to be 3s long:

```
butterflow -s a=1.5,b=2,dur=3 [video]
```

## Multiple regions
With two regions:

```
butterflow -s a=1,b=2,spd=0.5:a=9,b=end,spd=0.5 [video]
```

With four regions:

```
butterflow -s \
a=4.2,b=6,spd=0.125:\
a=6,b=6.8,dur=3:\
a=6.8,b=7,dur=0.4:\
a=20,b=end,fps=200 [video]
```

## Quality
Butterflow uses the Farneback algorithm to compute dense optical flows for frame
interpolation. You can pass in different values to the function to fine-tune the
quality (robustness of image) of the resulting videos. Run `butterflow -h` for a
list of advanced options and their default values.
