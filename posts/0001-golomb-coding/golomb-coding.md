---
title: Binary image compression with Golomb coding
date: August 13, 2023
---

## A Context for the Problem

Secret Agent 00111 has emerged from retirement, drawn back into the covert underworld for one final mission. Robot cars have cut their mechanical ties and are running loose in cities across America, wreaking unprecedented autonomous havoc. With the fate of humanity once again on the line, Agent 00111 may be the only man capable of returning these rogue automata to their low-bandwidth leash.

Recent advances in high-resolution lidar have provided robots with remarkable new faculties for sensing their environment, but the resulting onslaught of lidar data has swamped the global robot surveillance network, rendering terabytes of robot activity invisible to their human handlers.

Senior case officers working out of the Pittsburgh field office have developed a compression algorithm for lidar data.
By converting lidar point clouds to range images, they are using techniques from lossless image and video compression to regain control over the growing robot swarms.

![test image!](figures/scan.svg)

A declassified report from the signals intelligence (SIGINT) group has demonstrated excellent early progress, but one piece of the puzzle remains unsolved.
Lidar sensors produce out-of-range measurements whenever the lidar beam hits a surface that is too close or too far from the sensor.
The in-range/out-of-range status for each measurement can be stored in a binary image. In-range points are recorded as `0b1` (white), and out-of-range points are stored as `0b0` (black).

![test image!](figures/mask.svg)

Remembering his [legendary casino case file (1966)](references/golomb1966.pdf), agency officers have called Agent 00111 out of retirement to compress the binary in-range/out-of-range mask, reduce the strain on the global robot surveillance network, and safely return the robots to human oversight.

## Binary Image Compression

In the paper we wrote for [ICRA 2023](https://arxiv.org/abs/2209.08196), we used `numpy.packbits()` to pack the in-range/out-of-range bitmask into bytes---eight pixels per byte. We then applied [zstandard](http://facebook.github.io/zstd/) to compress the packed bytes. This approach worked well enough at the time, but I think we can do a lot better.

As I see it, there are two problems with the packbits+zstandard solution:

First, I suspect that packing the bits obscures pattern in the binary image data. Our bitmask images are full of "runs"---long stretches of zeros or ones---that are hidden by the packbits operation. This makes it harder for zstandard to find and exploit the "run" patterns in the original data.

Second, zstandard is massive overkill for this problem. Black-and-white image compression has been studied since the early 1960's when researchers were searching for efficient compression algorithms for high-resolution document scans. I expect we can design a simple solution that performs as-well or better than zstandard while being much simpler to understand and implement. With luck, we can remove the dependency on zstandard from our codebase and replace it with a few tens of lines of C.

### Run Length Encoding
Let's start off by exploiting the pattern of runs in the binary images. Run-length encoding is a classic compression technique that was developed for just this kind of problem. Instead of transmitting `0,0,1,1,1,1,1,1,1,1,1,1,1,1,0`, we can transmit `2,12,1`, the lengths of each run of identical values. If we're smart about how we encode the run lengths, we can likely achieve great compression!

In the following image, I have identified the runs of consecutive identical values and color-coded each run according to its length. Long runs are dark blue, shorter runs are green, and very short runs are orange and red.

![test image!](figures/runs.svg)

As you can see, there are many long runs of identical values that we can exploit using run-length encoding.
The longest runs occur when the lidar sensor scans empty sky (always out-of-range) or flat pavement (always in-range). In regions where the lidar passes through trees, the sensor alternates rapidly from in-range to out-of-range, creating thousands of very short runs in the image. A histogram of the run lengths illustrates their distribution.

![test image!](figures/histogram.svg)

This distribution of run lengths is vaguely geometric. Small values are far more frequent than large values. Let's try encoding them using Golomb codes.

### Golomb Coding
Simon Golomb developed his eponymous codes in 1966 and published their description in a spy-themed article whose content is much more entertaining than its title (*Run Length Encodings*). His Golomb codes are an optimal prefix code for alphabets that follow a geometric distribution like our run lengths. Better yet, implementing the Golomb code is straightforward, even if the math underlying them is fairly deep.

## Implementation

## Perspective
