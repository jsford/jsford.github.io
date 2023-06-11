---
title: Sort LiDAR point clouds 80x faster.
description: Avoid calling `atan2()` in your comparison function, and use a recent sorting algorithm like `pdqsort()`.
date: May 19, 2023
---

When working with LiDAR point clouds, I sometimes need to sort a scan full of points into counter-clockwise (or clockwise) scanlines.
I first encountered this problem while working on LiDAR mapping, and I recently re-encountered it in our work on LiDAR data compression.
In this article, I'll show you how I sped up the na&#239;ve sort by avoiding inverse trig functions in the sorting comparison function.
Even if you don't work with LiDAR, I think this is a fun problem that illustrates a general pattern you might find useful in other applications.

## Straightforward Sorting

The straightforward solution to this problem is to use `std::sort()` with a comparison function that compares points first by altitude angle and then by azimuth angle.
The altitude of a point is its angle above the sensor's X-Y plane. The azimuth of a point is its angle *around* the sensor---its yaw.

![A diagram showing the altitude and azimuth coordinates that define a LiDAR point in spherical coordinates](/posts/0000-sort-points/lidar-coordinates.svg)

Here is a comparison function that solves this problem using `std::atan()` and `std::atan2()`.

    bool SlowCompare(const Vector3f& v0, const Vector3f& v1) {
        float altitude0 = std::atan(v0.z / std::sqrt(v0.x*v0.x+v0.y*v0.y));
        float altitude1 = std::atan(v1.z / std::sqrt(v1.x*v1.x+v1.y*v1.y));

        // If points are not from the same scanline, compare their altitude angles.
        if( std::abs(altitude0 - altitude1) > 1e-8 ) {
            return altitude0 > altitude1; // Sort from top scanline to bottom.
        }

        // If points are from the same scanline, compare their azimuth angles.
        float azimuth0 = std::atan2(v0.y, v0.x);
        float azimuth1 = std::atan2(v1.y, v1.x);

        return azimuth0 < azimuth1; // Sort counterclockwise around the +Z axis.
    }

Then we can use `std::sort()` with the `CompareAtan2()` lambda to compare points.
Sadly, for large LiDAR point clouds, this approach can be pretty slow.

## Faster Comparison

My first instinct for speeding up this code was to find a way to avoid calls to `std::atan2()`.
This ended up being kinda fun!
If you've been programming anything math-y for a while, you've probably written something like this:

    if( std::sqrt(x*x+y*y) < R ) {
        // (x, y) is inside a circle of radius R.
    }

And hopefully you've noticed (or been taught) that you can avoid computing the call to `sqrt()` by squaring both sides of the comparison.

    if( (x*x+y*y) < R*R ) {
        // (x, y) is inside a circle of radius R.
    }

The `std::atan2()` function is fairly expensive --- it takes more than 100 ns to compute on my desktop.
Let's try speeding up the `CompareAtan2()` function by transforming the `atan2()`'s on both sides of the comparison into something cheaper to compute.

## Better Sorting Algorithm
Another, arguably more important, avenue for speeding up the point sorting process is to use a better sorting algorithm.
I dropped in `pdqsort()` as a replacement for `std::sort()`, and *wow* is it better!

## Benchmarks

| Method                              | Time [ms] | Std Dev [us] | Speedup |
|-------------------------------------|:---------:|:------------:|:-------:|
| std::sort() with SlowCompareAtan2() |   121.22  |      476     |   1.0x  |
| std::sort() with FastCompareAtan2() |    20.96  |      155     |   5.8x  |
| pdqsort()   with SlowCompareAtan2() |     8.88  |       53     |  13.7x  |
| pdqsort()   with FastCompareAtan2() |     1.58  |        8     |  76.7x  |

## Conclusions

* Use a good sorting algorithm like `pdqsort()`.
* Consider using a fast comparison predicate instead of `atan2()`.
