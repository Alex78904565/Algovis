"""Executable checks for the concrete Road Trip and TSP teaching examples."""

from __future__ import annotations

import itertools
import json
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def verify_road_trip() -> dict[str, object]:
    data = json.loads((ROOT / "assets/examples/road_trip.json").read_text())
    capacity = data["tank_capacity"]
    fuel_needed = data["fuel_per_segment"]
    prices = data["price_per_unit"]

    @lru_cache(maxsize=None)
    def solve(city: int, fuel: int) -> tuple[int, tuple[int, ...], tuple[int, ...]]:
        if city == len(fuel_needed):
            return 0, (), ()
        legal = range(max(0, fuel_needed[city] - fuel), capacity - fuel + 1)
        candidates = []
        for purchase in legal:
            arrival = fuel + purchase - fuel_needed[city]
            future_cost, future_purchases, future_arrivals = solve(city + 1, arrival)
            candidates.append(
                (
                    prices[city] * purchase + future_cost,
                    (purchase,) + future_purchases,
                    (arrival,) + future_arrivals,
                )
            )
        return min(candidates, key=lambda candidate: candidate[0])

    result = solve(0, data["start_fuel"])
    expected = data["expected"]
    assert result[0] == expected["minimum_cost"]
    assert list(result[1]) == expected["purchases"]
    assert list(result[2]) == expected["arrival_fuel"]
    return {"minimum_cost": result[0], "purchases": result[1], "arrival_fuel": result[2]}


def verify_tsp_path() -> dict[str, object]:
    data = json.loads((ROOT / "assets/examples/tsp_path.json").read_text())
    cities = data["cities"]

    def distance(a: str, b: str) -> int:
        return data["distances"]["-".join(sorted((a, b)))]

    candidates = []
    for tail in itertools.permutations(city for city in cities if city != data["start"]):
        path = (data["start"],) + tail
        cost = sum(distance(a, b) for a, b in zip(path, path[1:]))
        candidates.append((cost, path))
    optimum = min(cost for cost, _path in candidates)
    expected_path = tuple(data["expected"]["one_optimal_path"])
    assert optimum == data["expected"]["minimum_distance"]
    assert sum(distance(a, b) for a, b in zip(expected_path, expected_path[1:])) == optimum

    shared_states = []
    for history in data["reuse_example"]["histories"]:
        bits = tuple(int(city in history) for city in cities)
        shared_states.append((history[-1],) + bits)
    assert shared_states[0] == shared_states[1]
    assert list(shared_states[0]) == data["reuse_example"]["shared_state"]
    return {"minimum_distance": optimum, "path": expected_path, "shared_state": shared_states[0]}


if __name__ == "__main__":
    print("road_trip", verify_road_trip())
    print("tsp_path", verify_tsp_path())
