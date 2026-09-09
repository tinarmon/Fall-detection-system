"""Angle calculator module (backwards-compatibility facade)."""

from __future__ import annotations

from src.fall_detection.geometry import calculate_angle_2d, calculate_angle_3d


class AngleCalculator:
    """Backwards-compatible wrapper delegating to pure functional geometry routines."""

    @staticmethod
    def calculate_angle(a, b, c) -> float:
        return calculate_angle_2d(a, b, c)

    @staticmethod
    def calculate_angle_3d(a, b, c) -> float:
        return calculate_angle_3d(a, b, c)