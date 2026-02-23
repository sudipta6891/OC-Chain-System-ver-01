"""
Probability calibration engine (Platt + isotonic).
"""

from __future__ import annotations

import math


class ProbabilityCalibrationEngine:
    @staticmethod
    def _sigmoid(z: float) -> float:
        if z > 20:
            return 1.0
        if z < -20:
            return 0.0
        return 1.0 / (1.0 + math.exp(-z))

    @staticmethod
    def _fit_platt(samples: list[tuple[float, int]], iters: int = 200, lr: float = 0.1) -> tuple[float, float]:
        # p_cal = sigmoid(a * logit(p_raw) + b)
        a = 1.0
        b = 0.0
        for _ in range(iters):
            da = 0.0
            db = 0.0
            n = max(1, len(samples))
            for p_raw, y in samples:
                p_raw = max(1e-5, min(1 - 1e-5, p_raw))
                x = math.log(p_raw / (1 - p_raw))
                y_hat = ProbabilityCalibrationEngine._sigmoid(a * x + b)
                err = y_hat - y
                da += err * x
                db += err
            a -= lr * (da / n)
            b -= lr * (db / n)
        return a, b

    @staticmethod
    def _fit_isotonic(samples: list[tuple[float, int]]) -> list[tuple[float, float, float]]:
        # Pair-adjacent violators: blocks of (x_min, x_max, y_mean)
        points = sorted((x, float(y)) for x, y in samples)
        blocks: list[list[float]] = []  # x_min, x_max, sum_y, count
        for x, y in points:
            blocks.append([x, x, y, 1.0])
            while len(blocks) >= 2:
                b1 = blocks[-2]
                b2 = blocks[-1]
                m1 = b1[2] / b1[3]
                m2 = b2[2] / b2[3]
                if m1 <= m2:
                    break
                merged = [b1[0], b2[1], b1[2] + b2[2], b1[3] + b2[3]]
                blocks = blocks[:-2]
                blocks.append(merged)
        return [(b[0], b[1], b[2] / b[3]) for b in blocks]

    @staticmethod
    def _apply_isotonic(blocks: list[tuple[float, float, float]], p_raw: float) -> float:
        if not blocks:
            return p_raw
        p = max(0.0, min(1.0, p_raw))
        for x_min, x_max, y_mean in blocks:
            if x_min <= p <= x_max:
                return float(max(0.0, min(1.0, y_mean)))
        if p < blocks[0][0]:
            return float(max(0.0, min(1.0, blocks[0][2])))
        return float(max(0.0, min(1.0, blocks[-1][2])))

    @staticmethod
    def calibrate(
        raw_probability: float,
        samples: list[tuple[float, int]],
        min_samples: int = 30,
    ) -> dict:
        p_raw = max(0.01, min(0.99, raw_probability))
        if len(samples) < max(1, min_samples):
            return {
                "method": "identity_insufficient_samples",
                "calibrated_probability": p_raw,
                "sample_size": len(samples),
                "min_samples_required": int(max(1, min_samples)),
            }

        a, b = ProbabilityCalibrationEngine._fit_platt(samples)
        logit = math.log(p_raw / (1 - p_raw))
        p_platt = ProbabilityCalibrationEngine._sigmoid(a * logit + b)

        iso_blocks = ProbabilityCalibrationEngine._fit_isotonic(samples)
        p_iso = ProbabilityCalibrationEngine._apply_isotonic(iso_blocks, p_raw)

        # Blend platt and isotonic for stability.
        p_final = (0.6 * p_platt) + (0.4 * p_iso)
        return {
            "method": "platt_isotonic_blend",
            "calibrated_probability": max(0.01, min(0.99, p_final)),
            "sample_size": len(samples),
            "platt": p_platt,
            "isotonic": p_iso,
        }
