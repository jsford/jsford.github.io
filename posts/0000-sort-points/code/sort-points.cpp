#include "pdqsort.h"
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <math.h>
#include <random>
#include <vector>

struct Vector3f {
    float x, y, z;
};

std::vector<Vector3f> fakeLidarPoints(int linesPerScan, int pointsPerLine) {
    std::vector<Vector3f> points(linesPerScan * pointsPerLine);

    float minAlt = -15.0f * M_PI / 180.0f;
    float maxAlt = +15.0f * M_PI / 180.0f;
    float minAzi = -179.9f * M_PI / 180.0f; // Avoid wraparound annoyance at -180 degrees.
    float maxAzi = +179.9f * M_PI / 180.0f; // Avoid wraparound annoyance at +180 degrees.
    float maxRange = 100.0f;

    for (int i = 0; i < linesPerScan; ++i) {
        float altitude =
            (linesPerScan - i) / ((float)linesPerScan - 1) * (maxAlt - minAlt) + minAlt;
        for (int j = 0; j < pointsPerLine; ++j) {
            float azimuth = j / ((float)pointsPerLine + 1) * (maxAzi - minAzi) + minAzi;
            float range = rand() / (float)RAND_MAX * maxRange;
            points[i * pointsPerLine + j].x = range * std::sin(M_PI_2 - altitude) * std::cos(azimuth);
            points[i * pointsPerLine + j].y = range * std::sin(M_PI_2 - altitude) * std::sin(azimuth);
            points[i * pointsPerLine + j].z = range * std::cos(M_PI_2 - altitude);
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

inline bool CompareAltitudeAzimuthSlow(const Vector3f &v0, const Vector3f &v1) {
    float altitude0 = std::atan(v0.z / std::sqrt(v0.x * v0.x + v0.y * v0.y));
    float altitude1 = std::atan(v1.z / std::sqrt(v1.x * v1.x + v1.y * v1.y));

    // For this example, points are in the same scanline
    // if their altitudes match within 0.05 degrees.
    constexpr float dAltitude = 0.05f * M_PI / 180.0f;

    // If points are not from the same scanline, compare their altitude angles.
    if (std::abs(altitude0 - altitude1) > dAltitude) {
        return altitude0 > altitude1; // Sort from top scanline to bottom.
    }

    // If points are from the same scanline, compare their azimuth angles.
    float azimuth0 = std::atan2(v0.y, v0.x);
    float azimuth1 = std::atan2(v1.y, v1.x);

    return azimuth0 < azimuth1; // Sort counterclockwise around the +Z axis.
}

inline bool CompareAltitudeAzimuthFast(const Vector3f &v0, const Vector3f &v1) {
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

#define MAKE_POINT_SORTER(name, compare, sort)                                             \
    void name(std::vector<Vector3f> &points) {                                             \
        sort(std::begin(points), std::end(points), compare);                               \
    }

MAKE_POINT_SORTER(SortPointsA, CompareAltitudeAzimuthSlow, std::sort);
MAKE_POINT_SORTER(SortPointsB, CompareAltitudeAzimuthFast, std::sort);
MAKE_POINT_SORTER(SortPointsC, CompareAltitudeAzimuthSlow, pdqsort);
MAKE_POINT_SORTER(SortPointsD, CompareAltitudeAzimuthFast, pdqsort);

#define MAKE_POINT_SORT_CHECKER(name, compare)                                             \
    bool name(std::vector<Vector3f> &points) {                                             \
        return std::is_sorted(std::begin(points), std::end(points), compare);              \
    }

MAKE_POINT_SORT_CHECKER(ArePointsSortedA, CompareAltitudeAzimuthSlow);
MAKE_POINT_SORT_CHECKER(ArePointsSortedB, CompareAltitudeAzimuthFast);

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

    std::vector<Vector3f> points = fakeLidarPoints(128, 1024);
    std::vector<Vector3f> shuffledPoints = shufflePoints(points);

    // Benchmark sorting method A.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsA(tmp);
        auto t1 = now();
        printf("Sort A %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("A Failed!\n");
        }
    }

    // Benchmark sorting method B.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsB(tmp);
        auto t1 = now();
        printf("Sort B %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("B Failed!\n");
        }
    }

    // Benchmark sorting method C.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsC(tmp);
        auto t1 = now();
        printf("Sort C %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("C Failed!\n");
        }
    }

    // Benchmark sorting method D.
    {
        std::vector<Vector3f> tmp = shuffledPoints;
        auto t0 = now();
        SortPointsD(tmp);
        auto t1 = now();
        printf("Sort D %f ms\n", (t1 - t0) / 1e6);
        if (!AllClose(tmp, points)) {
            printf("D Failed!\n");
        }
    }

    // Benchmark sortedness checking method A.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        bool result = ArePointsSortedA(tmp);
        auto t1 = now();
        printf("IsSorted A %f ms\n", (t1 - t0) / 1e6);
        if( !result ) { printf("A Failed!\n"); }
    }

    // Benchmark sortedness checking method B.
    {
        std::vector<Vector3f> tmp = points;
        auto t0 = now();
        bool result = ArePointsSortedB(tmp);
        auto t1 = now();
        printf("IsSorted B %f ms\n", (t1 - t0) / 1e6);
        if( !result ) { printf("A Failed!\n"); }
    }

    return 0;
}
