---
title: Fast methods for sorting LiDAR point clouds.
date: May 19, 2023
---

Lately I've been working on fast algorithms for LiDAR compression and LiDAR mapping.
In both applications, I've run across a fun subproblem: *what is the fastest way to sort LiDAR point clouds into a canonical scan order?*

For the most part, LiDAR sensors emit points in a consistent top-down, counterclockwise order.
However LiDAR processing code usually can't assume scans are pre-sorted since sensor manufacturers are free to sort in whatever order is convenient,
and intermediate storage and filtering steps might accidentally reorder the data.

![A diagram showing the altitude and azimuth coordinates that define a LiDAR point in spherical coordinates](/posts/0000-sort-points/figures/lidar-coordinates.svg)

Since my LiDAR processing algorithms rely on consistently-ordered scans, I need fast methods to (1) check if a scan is already sorted and (2) sort scans that aren't already in scan order.

## How to sort LiDAR points (when you don't need to go fast).

At a high level, the goal is to take a pile of (x, y, z) points in any order and quickly sort them into counterclockwise-ordered scanlines.
In C++, the straightforward way to accomplish this is to use `std::sort()` with a custom point-comparison function.

The point-comparison function should accept two (x, y, z) points and decide which point goes first in the desired scan order.
If the first point should preceed the second point, the function should return `true`. Otherwise, it should return `false`.
With an appropriate point-comparison function, we can use `std::sort()` to sort an array of points into scan order.

    // Sort points into scan order using the CompareAltitudeAzimuth comparison function.
    // Points should be sorted into scanlines from highest altitude to lowest.
    // Points within each scanline should be sorted from least azimuth to greatest. 
    std::sort( std::begin(points), std::end(points), CompareAltitudeAzimuth );

The `CompareAltitudeAzimuth()` function is the custom comparison routine that defines the scan order.
In its most straightforward implementation, `CompareAltitudeAzimuth()` computes and compares the altitude and azimuth angles for both points.
If the two points have differing altitudes, they belong to separate scanlines, and the point with the higher elevation should be sorted first.
If both points have similar altitudes, they belong to the same scanline, so the point with the smaller azimuth should be sorted first.

    bool CompareAltitudeAzimuth(const Vector3f &v0, const Vector3f &v1) {
        // First, compare the altitudes of the two points.
        int compareAlt = CompareAltitude(v0, v1);

        // If the altitudes do not match, sort from highest altitude to lowest.
        if( compareAlt != 0 ) { return (compareAlt < 0); }

        // If the altitudes do match, sort by azimuth from least to greatest.
        return CompareAzimuth(v0, v1);
    }

`CompareAltitude()` is a function that computes and compares the altitude of both points.
It returns `+1` if the first point is at a lower elevation than the second,
`0` if the two points are at approximately the same elevation, and
`-1` if the first point is at a higher elevation than the second point.

    int CompareAltitude(const Vector3f& v0, const Vector3f& v1) {
        // Compute the altitude angle for each point.
        float altitude0 = std::atan(v0.z / std::sqrt(v0.x * v0.x + v0.y * v0.y));
        float altitude1 = std::atan(v1.z / std::sqrt(v1.x * v1.x + v1.y * v1.y));

        // For this example, two points are from the same scanline
        // if their altitudes match within 0.05 degrees.
        const float dAltitude = 0.05f * M_PI/180.0f;

        // If the altitudes match, return zero. 
        if (std::abs(altitude0 - altitude1) < dAltitude) {
            return 0;
        }

        // Return +1 if altitude0 is smaller.
        // Return -1 if altitude0 is larger.
        return (altitude0 < altitude1) ? 1 : -1;
    }

When two points' altitudes are within 0.05&deg;, they are considered part of the same LiDAR scanline.
In that case, the `CompareAzimuth()` function is used to decide which point comes first within the counterclockwise-ordered scanline.

    bool CompareAzimuthSlow(const Vector3f& v0, const Vector3f& v1) {
        // Compute the azimuth angle for each point.
        float azimuth0 = std::atan2(v0.y, v0.x);
        float azimuth1 = std::atan2(v1.y, v1.x);

        // Sort counterclockwise around the +Z axis.
        return (azimuth0 < azimuth1);
    }

Using `std::sort()` with `CompareAltitudeAzimuth()`, we can reliably sort LiDAR scans into our preferred scan order.
This method is great because it's straightforward and easy to explain, but for high-speed LiDAR processing, there are two problems with this approach:

1. This method calls `std::atan()`, `std::atan2()`, and `std::sqrt()` multiple times for every comparison.
   Since these functions take a long time to compute, the overall sorting method is fairly slow.
2. This method does not check whether points are already sorted.
   When the points are already in scan order, it will waste a significant amount of time re-sorting the sorted points.

## A faster method to compare altitudes.
The straightforward method for comparing altitude angles is slow because it uses `sqrt()` and `atan()` to compute the altitude angle for both points.
Instead of comparing the angles, what if we normalize both vectors and compare their z components?

Instead of this...

    // Compute the altitude angle for each point.
    float altitude0 = std::atan(v0.z / std::sqrt(v0.x * v0.x + v0.y * v0.y));
    float altitude1 = std::atan(v1.z / std::sqrt(v1.x * v1.x + v1.y * v1.y));

We can do this...

    float height0 = v0.z / std::sqrt(v0.x * v0.x + v0.y * v0.y);
    float height1 = v1.z / std::sqrt(v1.x * v1.x + v1.y * v1.y);

That avoids the calls to `atan()`, but what about the calls to `sqrt()`?
We can avoid calling `sqrt()` by comparing the squared heights instead.

    float squaredHeight0 = (v0.z*v0.z) / (v0.x * v0.x + v0.y * v0.y);
    float squaredHeight1 = (v1.z*v1.z) / (v1.x * v1.x + v1.y * v1.y);

But squaring the heights doesn't work unless both `v0.z` and `v1.z` are non-negative.
If the signs of the z coordinates are different, we can immediately decide which has a higher altitude.

    int sign0 = (v0.z >= 0) ? 1 : -1;
    int sign1 = (v1.z >= 0) ? 1 : -1;

    if( sign0 != sign1 ) { return (sign0 < sign1) ? 1 : -1; }

If the signs are the same, we can compare the squared heights safely, so long as we remember to swap the inequality when both signs are negative.
If we incorporate these changes into the original comparison function, we get something like this:

    int CompareAltitudeFast(const Vector3f& v0, const Vector3f& v1) {
        // Store the signs of the original Z coordinates.
        int sign0 = (v0.z >= 0) ? 1 : -1;
        int sign1 = (v1.z >= 0) ? 1 : -1;

        // If the Z coordinate signs don't match, return +/-1
        // to indicate which point has the higher altitude.
        if( sign0 != sign1 ) { return (sign0 < sign1) ? 1 : -1; }

        // If the signs of the Z coordinates do match, normalize
        // both points and compare the squared heights
        // of the resulting normalized vectors.
        float squaredHeight0 = (v0.z*v0.z / (v0.x*v0.x+v0.y*v0.y));
        float squaredHeight1 = (v1.z*v1.z / (v1.x*v1.x+v1.y*v1.y));

        // Since we aren't comparing angles any more, we have to convert
        // our 0.05 degree tolerance from degrees to units of squared height.
        constexpr float dAltitude = 0.05f * M_PI / 180.0f;
        constexpr float dHeight = std::sin(dAltitude);

        // If the squared heights are sufficiently similar,
        // return 0 to indicate they are from the same scanline.
        if( std::abs(squaredHeight1 - squaredHeight0) < dHeight*dHeight ) {
            return 0;
        }

        // If the squared heights are different, fix up their signs,
        // compare their squared heights, and return the result.
        return (sign0 * squaredHeight0 < sign1 * squaredHeight1) ? 1 : -1;
    }

This method avoids `sqrt()` and `atan2()`, but I suspect it has problems for points at large altitudes (>80&deg;) that I haven't yet resolved.
Basically, my current epsilon calculation is "good enough" for the LiDAR sensors I have been working with, but I expect it to fail at high altitudes.
I suspect a more robust calculation will be needed for sensors that produce points at more extreme altitudes.


## A faster method to compare azimuths.

    int Atan2Quadrant(float x, float y) {
        // This function identifies which quadrant an (x, y) coordinate falls within.
        // Quadrants are numbered in order from least to greatest atan2 value:
        //   3 | 2
        //   - - -
        //   0 | 1
        
        if (x >= 0.0f) {
            return (y >= 0.0f) ? 2 : 1;
        } else {
            return (y >= 0.0f) ? 3 : 0;
        }
    }

and...

    bool CompareAzimuthFast(const Vector3f& v0, const Vector3f& v1) {
        // Compute which quadrant each point lies within.
        uint8_t q0 = Atan2Quadrant(v0.x, v0.y);
        uint8_t q1 = Atan2Quadrant(v1.x, v1.y);

        // If the points fall in different quadrants, compare the quadrants.
        if (q0 != q1) {
            return q0 < q1;
        }

        // If the points fall in the same quadrant,
        // compute which octant they lie within.
        bool oct0 = (std::abs(v0.x) < std::abs(v0.y));
        bool oct1 = (std::abs(v1.x) < std::abs(v1.y));

        // If the points fall in different octants, compare the octants.
        if (oct0 != oct1) {
            // This statement is equivalent to the following:
            // if( q0 == 0 or q0 == 2 ) { return  oct1; }
            // if( q0 == 2 or q0 == 3 ) { return !oct1; }
            return (q0 & 0b1) ^ oct1;
        }

        // If the points fall in different octants, compare the ratios y/x.
        // Cross-multiply the ratios to turn divisions into multiplies.
        // This statement is equivalent to 
        //     return (v0.y / v0.x < v1.y / v1.x);
        return (v0.y * v1.x < v1.y * v0.x);
    }


## Don't sort if you don't need to.

Now that we have faster methods to compare altitudes and azimuths, we can combine them into a single comparison function and use them to sort point clouds.

    bool CompareAltitudeAzimuthFast(const Vector3f &v0, const Vector3f &v1) {
        int compareAlt = CompareAltitudeFast(v0, v1);
        if( compareAlt != 0 ) { return (compareAlt < 0); }

        return CompareAzimuthFast(v0, v1);
    }

Our fast comparison functions should help us sort disorganized point clouds significantly faster, but what happens if we give it an already-sorted point cloud?
In testing, `std::sort()` spends almost as much time sorting pre-sorted points as it would spend sorting randomly-ordered points.

For fun, let's try two methods to avoid wasting time sorting pre-sorted point clouds.

1. The first method will be to use `std::is_sorted()` to check if points are already sorted. If `std::is_sorted()` returns `true`, we can safely skip sorting.
2. The second method will be to replace `std::sort()` with [`pdqsort()`, a pattern-defeating quicksort](https://github.com/orlp/pdqsort).
   `pdqsort()` is an impressive recent sorting algorithm that should detect pre-sorted data and avoid wasting time by re-sorting it.

## Benchmark Results

To evaluate sorting performance, I generated a fake LiDAR scan containing 128 scanlines with 2048 points in each scanline.
For each scanline, I start at -180&deg; azimuth and sweep counterclockwise around the +Z axis.
With each new point, I increment or decrement the LiDAR range by a few centimeters, producing a random walk.
The resulting point cloud looks like a crayon doodle, but it's similar enough to real data for our benchmarks.

![alt text](/posts/0000-sort-points/figures/fake-lidar.svg)

The test points are generated in scan order, so I use `std::shuffle()` to randomize the order of the points.
Then for every combination of sorting method and comparison functions,
I sorted the shuffled points back into scan order and recorded the time elapsed.

| Sort shuffled points. | Compare Altitudes | Compare Azimuths | Time [ms] | Speedup |
|-----------------------|:-----------------:|:----------------:|:---------:|:--------:|
| `std::sort()`         |       Slow        |       Slow       |   143.38  |  1.00x  |
| `std::sort()`         |       Slow        |       Fast       |    82.02  |  1.75x  |
| `std::sort()`         |       Fast        |       Slow       |    92.11  |  1.55x  |
| `std::sort()`         |       Fast        |       Fast       |    34.50  |  4.16x  |
| `pdqsort()`           |       Slow        |       Slow       |   135.37  |  1.06x  |
| `pdqsort()`           |       Slow        |       Fast       |    77.64  |  1.85x  |
| `pdqsort()`           |       Fast        |       Slow       |    87.05  |  1.65x  |
| `pdqsort()`           |       Fast        |       Fast       |    32.87  |  4.36x  |

To evaluate performance on pre-sorted points, I repeated the same tests but without shuffling the points.

| Sort sorted points.   | Compare Altitudes | Compare Azimuths | Time [ms] | Speedup |
|-----------------------|:-----------------:|:----------------:|:---------:|:-------:|
| `std::sort()`         |       Slow        |       Slow       |   100.45  |  1.00x  |
| `std::sort()`         |       Slow        |       Fast       |    53.08  |  1.89x  |
| `std::sort()`         |       Fast        |       Slow       |    54.85  |  1.83x  |
| `std::sort()`         |       Fast        |       Fast       |    13.75  |  7.31x  |
| `pdqsort()`           |       Slow        |       Slow       |     8.07  | 12.44x  |
| `pdqsort()`           |       Slow        |       Fast       |     4.96  | 20.25x  |
| `pdqsort()`           |       Fast        |       Slow       |     4.07  | 24.68x  |
| `pdqsort()`           |       Fast        |       Fast       |     1.14  | 88.11x  |

Finally, I benchmarked a few variations of `std::is_sorted()` to see how fast we can check if a point cloud is already sorted.

| Check if points are sorted.  | Compare Altitudes | Compare Azimuths | Time [ms] | Speedup |
|------------------------------|:-----------------:|:----------------:|:---------:|:-------:|
| `std::is_sorted()`           |       Slow        |       Slow       |    5.72   |   1.0x  |
| `std::is_sorted()`           |       Slow        |       Fast       |    2.63   |   2.2x  |
| `std::is_sorted()`           |       Fast        |       Slow       |    3.69   |   1.6x  |
| `std::is_sorted()`           |       Fast        |       Fast       |    0.86   |   6.7x  |

Checking if points are sorted is already a fast operation, but using our fast comparison functions, we can still achieve a pretty decent 6.7x speedup!

## Conclusions

Sorting point clouds into a consistent scan order is an important pre-processing step for working with LiDAR point clouds.
The baseline sorting method computes altitude and azimuth angles and compares them directly.
This method is easy to explain, but it's slow because it relies on square roots and inverse trig functions.

By manipulating both sides of the comparison inequalities, we can avoid these slow operations and achieve a fairly good speedup.
Where the baseline sort method takes about 136 ms to organize a LiDAR scan, our improved method requires only 34 ms---a speedup of about 4x!

Most of the time, you shouldn't use these methods, since they introduce a fair amount of additional complication and only save a few milliseconds per scan.
But for some applications, those milliseconds really add up!
Regardless, this is a fun example of a generally useful tool. Often, you can manipulate both sides of a comparison to avoid computations and go a lot faster.

Messy code for this experiment is available [here](/posts/0000-sort-points/code).
