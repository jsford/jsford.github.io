#include "pdqsort.h"
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cmath>
#include <random>
#include <vector>

#include <fstream>

struct Vector3f {
    float x, y, z;
    bool operator==(const Vector3f& r) const { return r.x==x && r.y==y && r.z==z; }
};

std::vector<Vector3f> fakeLidarPoints(int linesPerScan, int pointsPerLine) {
    std::vector<Vector3f> points(linesPerScan * pointsPerLine);

    float minAlt = -15.0f * M_PI / 180.0f;
    float maxAlt = +15.0f * M_PI / 180.0f;
    float minAzi = -179.9f * M_PI / 180.0f; // Avoid wraparound annoyance at -180 degrees.
    float maxAzi = +179.9f * M_PI / 180.0f; // Avoid wraparound annoyance at +180 degrees.
    float minRange =   3.0f;
    float maxRange = 100.0f;

    std::vector<float> ranges(128);
    for(int i=0; i < linesPerScan; ++i) {
        ranges[i] = (rand() / (float)RAND_MAX) * (maxRange-minRange) + minRange;
    }

    for (int i = 0; i < linesPerScan; ++i) {
        float altitude =
            (linesPerScan - i) / ((float)linesPerScan - 1) * (maxAlt - minAlt) + minAlt;
        for (int j = 0; j < pointsPerLine; ++j) {
            float azimuth = j / ((float)pointsPerLine + 1) * (maxAzi - minAzi) + minAzi;

            float drange = 0.5 * (rand() / (float)RAND_MAX) - 0.25;
            ranges[i] = std::clamp(ranges[i]+drange, minRange, maxRange);

            points[i * pointsPerLine + j].x = ranges[i] * std::sin(M_PI_2 - altitude) * std::cos(azimuth);
            points[i * pointsPerLine + j].y = ranges[i] * std::sin(M_PI_2 - altitude) * std::sin(azimuth);
            points[i * pointsPerLine + j].z = ranges[i] * std::cos(M_PI_2 - altitude);
        }
    }
    return points;
}

std::vector<Vector3f> shufflePoints(const std::vector<Vector3f> points) {
    std::vector<Vector3f> shuffledPoints = points;

    auto rng = std::default_random_engine{};
    std::shuffle(std::begin(shuffledPoints), std::end(shuffledPoints), rng);
    return shuffledPoints;
}

inline int CompareAltitudeSlow(const Vector3f& v0, const Vector3f& v1) {
    float altitude0 = std::atan(v0.z / std::sqrt(v0.x * v0.x + v0.y * v0.y));
    float altitude1 = std::atan(v1.z / std::sqrt(v1.x * v1.x + v1.y * v1.y));

    const float dAltitude = 0.05f * M_PI/180.0f;

    // If points are not from the same scanline, compare their altitude angles.
    if (std::abs(altitude0 - altitude1) < dAltitude) {
        return 0;
    }
    return (altitude0 < altitude1) ? 1 : -1;
}

inline bool CompareAzimuthSlow(const Vector3f& v0, const Vector3f& v1) {
    float azimuth0 = std::atan2(v0.y, v0.x);
    float azimuth1 = std::atan2(v1.y, v1.x);

    return (azimuth0 < azimuth1); // Sort counterclockwise around the +Z axis.
}

inline int CompareAltitudeFast(const Vector3f& v0, const Vector3f& v1) {
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

inline bool CompareAzimuthFast(const Vector3f& v0, const Vector3f& v1) {
    // We number the quadrants in the order of least to greatest atan2 value.
    // This ordering simplifies later conditionals.
    //
    // Quadrants:
    //   3 | 2
    //   -----
    //   0 | 1

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
}

#define MAKE_COMPARISON(name, CompareAlt, CompareAzi)   \
    bool name(const Vector3f& v0, const Vector3f& v1) { \
        int res = CompareAlt(v0, v1);                   \
        if(  res != 0 ) { return (res < 0); }           \
        return CompareAzi(v0, v1);                      \
    }

MAKE_COMPARISON(CompareSlowSlow, CompareAltitudeSlow, CompareAzimuthSlow);
MAKE_COMPARISON(CompareSlowFast, CompareAltitudeSlow, CompareAzimuthFast);
MAKE_COMPARISON(CompareFastSlow, CompareAltitudeFast, CompareAzimuthSlow);
MAKE_COMPARISON(CompareFastFast, CompareAltitudeFast, CompareAzimuthFast);

#define MAKE_POINT_SORTER(name, compare, sort)                                             \
    void name(std::vector<Vector3f> &points) {                                             \
        sort(std::begin(points), std::end(points), compare);                               \
    }

MAKE_POINT_SORTER(SortPointsStdSlowSlow, CompareSlowSlow, std::sort);
MAKE_POINT_SORTER(SortPointsStdSlowFast, CompareSlowFast, std::sort);
MAKE_POINT_SORTER(SortPointsStdFastSlow, CompareFastSlow, std::sort);
MAKE_POINT_SORTER(SortPointsStdFastFast, CompareFastFast, std::sort);

MAKE_POINT_SORTER(SortPointsPdqSlowSlow, CompareSlowSlow, pdqsort);
MAKE_POINT_SORTER(SortPointsPdqSlowFast, CompareSlowFast, pdqsort);
MAKE_POINT_SORTER(SortPointsPdqFastSlow, CompareFastSlow, pdqsort);
MAKE_POINT_SORTER(SortPointsPdqFastFast, CompareFastFast, pdqsort);

#define MAKE_POINT_SORT_CHECKER(name, compare)                                             \
    bool name(std::vector<Vector3f> &points) {                                             \
        return std::is_sorted(std::begin(points), std::end(points), compare);              \
    }

MAKE_POINT_SORT_CHECKER(IsSortedSlowSlow, CompareSlowSlow);
MAKE_POINT_SORT_CHECKER(IsSortedSlowFast, CompareSlowFast);
MAKE_POINT_SORT_CHECKER(IsSortedFastSlow, CompareFastSlow);
MAKE_POINT_SORT_CHECKER(IsSortedFastFast, CompareFastFast);

int64_t now() {
    using namespace std::chrono;
    return high_resolution_clock::now().time_since_epoch() / nanoseconds(1);
}

bool AllClose(const std::vector<Vector3f> &v0, const std::vector<Vector3f> &v1,
              float epsilon = 1e-6) {
    if (v0.size() != v1.size()) {
        return false;
    }
    for (int i = 0; i < v0.size(); ++i) {
        if (std::abs(v0[i].x - v1[i].x) > epsilon) {
            return false;
        }
        if (std::abs(v0[i].y - v1[i].y) > epsilon) {
            return false;
        }
        if (std::abs(v0[i].z - v1[i].z) > epsilon) {
            return false;
        }
    }
    return true;
}

int main(int argc, char *argv[]) {

    std::vector<Vector3f> points = fakeLidarPoints(128, 2048);
    std::vector<Vector3f> shuffledPoints = shufflePoints(points);

    // Benchmark sorting with std::sort, CompareAltitudeSlow, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsStdSlowSlow(tmp);
        auto t1 = now();
        printf("[Sort Shuffled]  std slow slow %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting with std::sort, CompareAltitudeSlow, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsStdSlowFast(tmp);
        auto t1 = now();
        printf("[Sort Shuffled]  std slow fast %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting with std::sort, CompareAltitudeFast, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsStdFastSlow(tmp);
        auto t1 = now();
        printf("[Sort Shuffled]  std fast slow %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting with std::sort, CompareAltitudeFast, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsStdFastFast(tmp);
        auto t1 = now();
        printf("[Sort Shuffled]  std fast fast %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }

    printf("\n");

    // Benchmark sorting with pdqsort, CompareAltitudeSlow, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsPdqSlowSlow(tmp);
        auto t1 = now();
        printf("[Sort Shuffled]  pdq slow slow %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting with pdqsort, CompareAltitudeSlow, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsPdqSlowFast(tmp);
        auto t1 = now();
        printf("[Sort Shuffled]  pdq slow fast %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting with pdqsort, CompareAltitudeFast, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsPdqFastSlow(tmp);
        auto t1 = now();
        printf("[Sort Shuffled]  pdq fast slow %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting with pdqsort, CompareAltitudeFast, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsPdqFastFast(tmp);
        auto t1 = now();
        printf("[Sort Shuffled]  pdq fast fast %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }

    printf("\n");

    // Benchmark sorting sorted data with std::sort, CompareAltitudeSlow, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        SortPointsStdSlowSlow(tmp);
        auto t1 = now();
        printf("[Sort Sorted]    std slow slow %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting sorted data with std::sort, CompareAltitudeSlow, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        SortPointsStdSlowFast(tmp);
        auto t1 = now();
        printf("[Sort Sorted]    std slow fast %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting sorted data with std::sort, CompareAltitudeFast, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        SortPointsStdFastSlow(tmp);
        auto t1 = now();
        printf("[Sort Sorted]    std fast slow %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting sorted data with std::sort, CompareAltitudeFast, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        SortPointsStdFastFast(tmp);
        auto t1 = now();
        printf("[Sort Sorted]    std fast fast %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }

    printf("\n");

    // Benchmark sorting sorted data with pdqsort, CompareAltitudeSlow, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        SortPointsPdqSlowSlow(tmp);
        auto t1 = now();
        printf("[Sort Sorted]    pdq slow slow %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting sorted data with pdqsort, CompareAltitudeSlow, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        SortPointsPdqSlowFast(tmp);
        auto t1 = now();
        printf("[Sort Sorted]    pdq slow fast %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting sorted data with pdqsort, CompareAltitudeFast, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        SortPointsPdqFastSlow(tmp);
        auto t1 = now();
        printf("[Sort Sorted]    pdq fast slow %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }
    // Benchmark sorting sorted data with pdqsort, CompareAltitudeFast, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        SortPointsPdqFastFast(tmp);
        auto t1 = now();
        printf("[Sort Sorted]    pdq fast fast %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("Failed!\n");
        }
    }

    printf("\n");

    // Benchmark sortedness checking with is_sorted, CompareAltitudeSlow, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        bool result = IsSortedSlowSlow(tmp);
        auto t1 = now();
        printf("[Check]          is_sorted slow slow %f ms\n", (t1 - t0) / 1e6);
        if( !result ) { printf("Failed!\n"); }
    }
    // Benchmark sortedness checking with is_sorted, CompareAltitudeSlow, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        bool result = IsSortedSlowFast(tmp);
        auto t1 = now();
        printf("[Check]          is_sorted slow fast %f ms\n", (t1 - t0) / 1e6);
        if( !result ) { printf("Failed!\n"); }
    }
    // Benchmark sortedness checking with is_sorted, CompareAltitudeFast, CompareAzimuthSlow.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        bool result = IsSortedFastSlow(tmp);
        auto t1 = now();
        printf("[Check]          is_sorted fast slow %f ms\n", (t1 - t0) / 1e6);
        if( !result ) { printf("Failed!\n"); }
    }
    // Benchmark sortedness checking with is_sorted, CompareAltitudeFast, CompareAzimuthFast.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        bool result = IsSortedFastFast(tmp);
        auto t1 = now();
        printf("[Check]          is_sorted fast fast %f ms\n", (t1 - t0) / 1e6);
        if( !result ) { printf("Failed!\n"); }
    }

    std::ofstream f("points.xyz");
    for(const auto& pt : points) {
        f << pt.x << "," << pt.y << "," << pt.z << "\n";
    }
    f.close();

    return 0;
}
