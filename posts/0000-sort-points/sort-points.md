---
title: Fast methods for sorting LiDAR point clouds.
date: May 19, 2023
---

1. Lately I've been working on LiDAR compression algorithms.
2. My compression algorithms rely on sorted point clouds, but sensor manufacturer's are not consistent with their ordering.
3. So, my compression algorithm needs to (1) check if points are in the right order and (2) sort them into the right order if they aren't.


## Baseline Sorting

The straightforward solution to this problem is to use `std::sort()` with a comparison function that compares points first by altitude angle and then by azimuth angle.
The altitude of a point is its angle above the sensor's X-Y plane. The azimuth of a point is its angle around the sensor---its yaw.

![A diagram showing the altitude and azimuth coordinates that define a LiDAR point in spherical coordinates](/posts/0000-sort-points/figures/lidar-coordinates.svg)

Here's a C++ function that compares the altitude angles of two points.
This function returns `+1` if the first point is at a lower elevation than the second,
`0` if the two points are at approximately the same elevation, and
`-1` if the first point is at a higher elevation than the second.

    int CompareAltitudeSlow(const Vector3f& v0, const Vector3f& v1) {
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

This function is fairly slow because it calls `std::atan()` and `std::sqrt()` to compute the altitude for each point.
Later, we'll look for ways to remove these, but for now let's look at the baseline comparison for azimuth angles.

    bool CompareAzimuthSlow(const Vector3f& v0, const Vector3f& v1) {
        // Compute the azimuth angle for each point.
        float azimuth0 = std::atan2(v0.y, v0.x);
        float azimuth1 = std::atan2(v1.y, v1.x);

        // Sort counterclockwise around the +Z axis.
        return (azimuth0 < azimuth1);
    }

This function is even more straightforward.
We use `std::atan2()` to compute the azimuth for each point, and we return a boolean to indicate which point has the smaller azimuth angle.

In order to sort points by altitude and then by azimuth, we need to combine our functions into a single comparison function.
This function first compares two points by their altitude angles.
If the altitude angles are the same, it breaks the tie by comparing the azimuth angles.

    bool CompareAltitudeAzimuthSlow(const Vector3f &v0, const Vector3f &v1) {
        // First, compare the altitudes of the two points.
        int compareAlt = CompareAltitudeSlow(v0, v1);

        // If the altitudes do not match, sort from highest altitude to lowest.
        if( compareAlt != 0 ) { return (compareAlt < 0); }

        // If the altitudes do match, sort by azimuth from least to greatest.
        return CompareAzimuthSlow(v0, v1);
    }

With this comparison function, we can now sort point clouds using `std::sort()`.

    // Sort points into scan order.
    // Scanlines will be sorted from highest altitude to lowest.
    // Points within each scanline will be sorted ccw from least to greatest azimuth.
    std::sort( std::begin(points), std::end(points), CompareAltitudeAzimuthSlow );

This code will reliably sort disorganized point clouds into scan order, but since it makes a lot of calls to `sqrt()`, `atan()`, and `atan2()`, it is fairly slow.
Let's see what we can do to make it go faster!

## Comparing Altitudes Faster
The baseline method for comparing altitude angles is slow because it uses `sqrt()` and `atan()` to compute the altitude angles for both points.

    int CompareAltitudeFast(const Vector3f& v0, const Vector3f& v1) {
        int sign0 = (v0.z >= 0) ? 1 : -1;
        int sign1 = (v1.z >= 0) ? 1 : -1;

        if( sign0 != sign1 ) { return (sign0 < sign1) ? 1 : -1; }

        float fakeAltitude0 = (v0.z*v0.z / (v0.x*v0.x+v0.y*v0.y));
        float fakeAltitude1 = (v1.z*v1.z / (v1.x*v1.x+v1.y*v1.y));

        constexpr float dAltitude = 0.05f * M_PI / 180.0f;
        constexpr float epsilon = std::sin(dAltitude);
        constexpr float fakeEpsilon = epsilon*epsilon;

        if( std::abs(fakeAltitude1 - fakeAltitude0) < fakeEpsilon ) {
            return 0;
        }
        return (sign0 * fakeAltitude0 < sign1 * fakeAltitude1) ? 1 : -1;
    }

## Comparing Azimuths Faster

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


## Sorting Faster

Now that we have faster methods to compare altitudes and azimuths, we can combine them into a single comparison function and use them to sort point clouds.

    bool CompareAltitudeAzimuthFast(const Vector3f &v0, const Vector3f &v1) {
        int compareAlt = CompareAltitudeFast(v0, v1);
        if( compareAlt != 0 ) { return (compareAlt < 0); }

        return CompareAzimuthFast(v0, v1);
    }

While we're here, let's try using a sorting algorithm other than `std::sort()`.
`pdqsort()` is a recent sorting algorithm that combines a ton of clever tricks to defeat patterns and make best use of your cache hierarchy.
It's a drop-in replacement for `std::sort()`, so let's test it as well.

    // Sort points into counterclockwise-ordered scanlines.
    pdqsort( std::begin(points), std::end(points), CompareAltitudeAzimuthFast );


## Benchmark Results

To evaluate sorting performance, I generated a fake LiDAR scan containing 128 scanlines with 2048 points in each scanline.
Then I used `std::shuffle()` to randomize the order of the points.
For each sorting method, I sorted the shuffled points back into scan order and measured the elapsed time.

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


I also benchmarked the time required to check if a scan is sorted.
Several LiDAR manufacturers produce points in sorted order, so it's not uncommon that the points will already be sorted.
In my compression code, I use `std::is_sorted()` to check if the points are sorted. That way I can skip sorting when it's not needed.

| Check if points are sorted.  | Compare Altitudes | Compare Azimuths | Time [ms] | Speedup |
|------------------------------|:-----------------:|:----------------:|:---------:|:-------:|
| `std::is_sorted()`           |       Slow        |       Slow       |    5.72   |   1.0x  |
| `std::is_sorted()`           |       Slow        |       Fast       |    2.63   |   2.2x  |
| `std::is_sorted()`           |       Fast        |       Slow       |    3.69   |   1.6x  |
| `std::is_sorted()`           |       Fast        |       Fast       |    0.86   |   6.7x  |

Checking if points are sorted is already a fast operation, but using our fast comparison functions, we can still achieve a pretty decent 6.5x speedup!

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
