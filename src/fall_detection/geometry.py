"""Geometric calculations for 2D and 3D joint angles."""

from __future__ import annotations

import numpy as np


def calculate_angle_2d(
    a: list[float] | np.ndarray,
    b: list[float] | np.ndarray,
    c: list[float] | np.ndarray,
) -> float:
    """Calculates the 2D planar angle in degrees at vertex point b between endpoints a and c.

    Parameters:
        a: (x, y) coordinates of first endpoint (e.g. shoulder).
        b: (x, y) coordinates of vertex point (e.g. hip).
        c: (x, y) coordinates of second endpoint (e.g. knee).

    Returns:
        Angle in degrees in the range [0.0, 180.0].
    """
    arr_a = np.asarray(a, dtype=np.float64)
    arr_b = np.asarray(b, dtype=np.float64)
    arr_c = np.asarray(c, dtype=np.float64)

    radians = np.arctan2(arr_c[1] - arr_b[1], arr_c[0] - arr_b[0]) - np.arctan2(
        arr_a[1] - arr_b[1], arr_a[0] - arr_b[0]
    )
    angle = np.abs(radians * (180.0 / np.pi))
    if angle > 180.0:
        angle = 360.0 - angle
    return float(angle)


def calculate_angle_3d(
    a: list[float] | np.ndarray,
    b: list[float] | np.ndarray,
    c: list[float] | np.ndarray,
) -> float:
    """Calculates the 3D angle in degrees at vertex b between vectors (a - b) and (c - b).

    Parameters:
        a: (x, y, z) coordinates of first endpoint in meters or normalized units.
        b: (x, y, z) coordinates of vertex point.
        c: (x, y, z) coordinates of second endpoint.

    Returns:
        Angle in degrees in the range [0.0, 180.0]. Returns 180.0 if either vector has zero length.
    """
    arr_a = np.asarray(a, dtype=np.float64)
    arr_b = np.asarray(b, dtype=np.float64)
    arr_c = np.asarray(c, dtype=np.float64)

    u = arr_a - arr_b
    v = arr_c - arr_b

    norm_u = np.linalg.norm(u)
    norm_v = np.linalg.norm(v)

    if norm_u == 0.0 or norm_v == 0.0:
        return 180.0

    cosine = np.dot(u, v) / (norm_u * norm_v)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))
