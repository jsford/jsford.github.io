---
title: A faster method to sort LiDAR point clouds.
date: May 19, 2023
---

When working with LiDAR point clouds, I sometimes need to sort a scan full of points into counter-clockwise (or clockwise) scanlines.
I first encountered this problem while working on LiDAR mapping, and I recently re-encountered it in our work on LiDAR data compression.
In this article, I'll show you how I sped up the na&#239;ve sort by avoiding inverse trig functions in the sorting comparison function.
Even if you don't work with LiDAR, I think this is a fun problem that illustrates a general pattern you might find useful in other applications.

The straightforward solution to this problem is to use `std::sort()` with a comparison function that compares points first by altitude angle and then by azimuth angle.
The altitude of a point is its angle above the sensor's X-Y plane. The azimuth of a point is its angle around the sensor---its yaw.

![A diagram showing the altitude and azimuth coordinates that define a LiDAR point in spherical coordinates](/posts/0000-sort-points/figures/lidar-coordinates.svg)

Here's a C++ implementation of the straightforward solution that uses `std::atan()` and `std::atan2()` to compute the altitude and azimuth angles for every point.

    bool CompareAltitudeAzimuth(const Vector3f& v0, const Vector3f& v1) {
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

With this comparison function, we can then sort a point cloud using `std::sort()`.

    // Sort points into counterclockwise-ordered scanlines.
    std::sort( std::begin(points), std::end(points), CompareAltitudeAzimuth );

If you aren't super worried about runtime speed, this is definitely the solution you should use.
It's clear and maintainable, but unfortunately it's pretty slow.

## Compare Altitudes Without `atan()`

Here is the before...

    float altitude0 = std::atan(v0.z / std::sqrt(v0.x*v0.x+v0.y*v0.y));
    float altitude1 = std::atan(v1.z / std::sqrt(v1.x*v1.x+v1.y*v1.y));

    // If points are not from the same scanline, compare their altitude angles.
    if( std::abs(altitude0 - altitude1) > 1e-8 ) {
        return altitude0 > altitude1; // Sort from top scanline to bottom.
    }

Here is the after...

    // Instead of computing altitudes, normalize the vectors and compare their z heights.
    float fakeAltitude0 = v0.z / std::sqrt(v0.x * v0.x + v0.y * v0.y + v0.z * v0.z);
    float fakeAltitude1 = v1.z / std::sqrt(v1.x * v1.x + v1.y * v1.y + v1.z * v1.z);

    // For this example, points are in the same scanline
    // if their altitudes match within 0.05 degrees.
    constexpr float dAltitude = 0.05f * M_PI / 180.0f;
    constexpr float dZ_at_1m = std::sin(dAltitude);

    // If points are not from the same scanline, compare their altitude angles.
    if (std::abs(fakeAltitude0 - fakeAltitude1) > dZ_at_1m) {
        return fakeAltitude0 > fakeAltitude1; // Sort from top scanline to bottom.
    }

## Compare Azimuths Without `atan2()`

Here is the before...

        // If points are from the same scanline, compare their azimuth angles.
        float azimuth0 = std::atan2(v0.y, v0.x);
        float azimuth1 = std::atan2(v1.y, v1.x);

        return azimuth0 < azimuth1; // Sort counterclockwise around the +Z axis.

Here is the after...

    auto Atan2Quadrant = [](float x, float y) -> uint8_t {
        if (x >= 0.0f) {
            return (y >= 0.0f) ? 2 : 1;
        } else {
            return (y >= 0.0f) ? 3 : 0;
        }
    };

    uint8_t q0 = Atan2Quadrant(v0.x, v0.y);
    uint8_t q1 = Atan2Quadrant(v1.x, v1.y);

    // Different quadrant!
    if (q0 != q1) {
        return q0 < q1;
    }

    // Same quadrant! Which octant?
    bool oct0 = (std::fabs(v0.x) < std::fabs(v0.y));
    bool oct1 = (std::fabs(v1.x) < std::fabs(v1.y));

    // Different octant!
    // if( (q0 == 0 or q0 == 2) and oct0 != oct1 ) { return oct1; }
    // if( (q0 == 1 or q0 == 3) and oct0 != oct1 ) { return !oct1; }
    if (oct0 != oct1) {
        return (q0 & 0b1) ^ oct1;
    }

    // Same octant!
    return v0.y * v1.x < v1.y * v0.x;

## Switch to `pdqsort()`
Another avenue for speeding up the point sorting process is to use a better sorting algorithm.
I dropped in `pdqsort()` as a replacement for `std::sort()`, and *wow* is it better!

## Benchmark Results

| Sort shuffled points.                         | Time [ms] | Speedup |
|-----------------------------------------------|:---------:|:-------:|
| std::sort() with CompareAltitudeAzimuthSlow() |    69.57  |   1.0x  |
| std::sort() with CompareAltitudeAzimuthFast() |    20.42  |   3.4x  |
| pdqsort()   with CompareAltitudeAzimuthSlow() |    61.77  |   1.1x  |
| pdqsort()   with CompareAltitudeAzimuthFast() |    18.54  |   3.8x  |



| Check if points are sorted.              | Time [ms] | Speedup |
|------------------------------------------|:---------:|:-------:|
| std::is_sorted() with SlowCompareAtan2() |    2.85   |   1.0x  |
| std::is_sorted() with FastCompareAtan2() |    0.44   |   6.4x  |

## Conclusions

* Use a good sorting algorithm like `pdqsort()`.
* Consider using a fast comparison predicate instead of `atan2()`.

All code for this experiment is available [here](/posts/0000-sort-points/code).
