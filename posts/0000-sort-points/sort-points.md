---
title: Sort LiDAR points into raster scan order 80x faster.
description: do something cool!
date: May 19, 2023
---

Lately I've been having a lot of fun working on LiDAR mapping algorithms and developing new compression codecs for LiDAR sensor data.
In both applications, I find myself needing to quickly verify that points given to my code are in scan order.
If they aren't in scan order, I need to quickly sort them into scan order before I continue working with them.

## The Straightforward Approach

The straightforward way to sort points within a scanline is to compute their azimuth angle using `atan2()`.

    bool CompareAtan2(const Vector2f& v0, const Vector2f& v1) {
        return std::atan2(v0.y, v0.x) < std::atan2(v1.y, v1.x);
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

* `std::sort()` with `CompareAtan2()` takes 200ms.
* `std::sort() with `FastCompareAtan2()` takes 40ms.
* `pdqsort()` with `CompareAtan2()` takes 120ms.
* `pdqsort()` with `FastCompareAtan2()` takes only 3ms!

## Conclusions

* Use a good sorting algorithm like `pdqsort()`.
* Consider using a fast comparison predicate instead of `atan2()`.
