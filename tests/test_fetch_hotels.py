import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import fetch_hotels_overpass as fh  # noqa: E402


def test_count_within_radius_uses_real_distance():
    resort = np.array([[46.0, 8.0]])
    # 0.05 deg latitude = 5.6 km (inside); 0.05 deg longitude at 46 N = 3.9 km (inside);
    # 0.2 deg latitude = 22 km (outside); a far point
    hotels = np.array([[46.05, 8.0], [46.0, 8.05], [46.2, 8.0], [47.5, 9.5]])
    assert fh.count_within_km(resort, hotels, 10.0) == [2]


def test_east_west_distance_shrinks_with_latitude():
    """A 2-D degree buffer would count both points; the true distance of the second is 13.9 km."""
    resort = np.array([[47.0, 8.0]])
    hotels = np.array([[47.0, 8.10], [47.0, 8.20]])   # 7.6 km and 15.2 km at 47 N
    assert fh.count_within_km(resort, hotels, 10.0) == [1]


def test_no_hotels_gives_zero():
    assert fh.count_within_km(np.array([[46.0, 8.0], [47.0, 9.0]]), np.empty((0, 2)), 10.0) == [0, 0]


def test_elements_nodes_and_way_centres():
    elements = [
        {"type": "node", "lat": 46.1, "lon": 8.1},
        {"type": "way", "center": {"lat": 46.2, "lon": 8.2}},
        {"type": "relation"},
    ]
    points = fh.elements_to_points(elements)
    assert points.shape == (2, 2)


def test_query_contains_nodes_ways_and_stars_filter():
    query = fh.build_query(45.0, 5.0, 48.0, 16.0)
    assert 'node["tourism"="hotel"]["stars"~"^[45]"]' in query
    assert 'way["tourism"="hotel"]["stars"~"^[45]"]' in query
    assert "out center" in query
