"""Checks preventing mixed model settings and incorrect measured group means."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from snow_validation import request_spec, pair_sources
from snow_plain_summary import measured_elevation_summary


class SnowMethodTests(unittest.TestCase):
    def test_grid_selection_has_separate_cache_identity(self):
        station=SimpleNamespace(lat=46.,lon=8.,elev_m=1321)
        old,key_old=request_spec(station,1995)
        new,key_new=request_spec(station,1995,cell_selection="nearest")
        self.assertNotEqual(key_old,key_new)
        self.assertEqual(parse_qs(urlparse(old).query)["cell_selection"],["land"])
        self.assertEqual(parse_qs(urlparse(new).query)["cell_selection"],["nearest"])

    def test_nearest_result_requires_explicit_matching_setting(self):
        station=SimpleNamespace(lat=46.,lon=8.,elev_m=1321)
        url,_=request_spec(station,1995,cell_selection="nearest")
        obs=pd.DataFrame([{"station_id":"AAA","winter":1995,"period":"past","snow_days_30cm":63,
                           "observed_days":136,"elev_m":1321,"lat":46.,"lon":8.}])
        models=pd.DataFrame([{"station_id":"AAA","winter":1995,"period":"past","model_days_06utc":121,
                              "model_days_daily_max":122,"model_observed_days":136,"model_hours":3264,
                              "query_elev_m":1321,"cell_selection":"nearest","request_url":url}])
        with self.assertRaisesRegex(ValueError,"mix"):
            pair_sources(obs,models)
        self.assertEqual(pair_sources(obs,models,cell_selection="nearest").error_days.iloc[0],58)

    def observations(self):
        return pd.DataFrame([
            {"station_id":"AAA","winter":1995,"period":"past","elev_m":1499,"snow_days_30cm":60},
            {"station_id":"AAA","winter":2025,"period":"recent","elev_m":1499,"snow_days_30cm":40},
            {"station_id":"BBB","winter":1995,"period":"past","elev_m":1500,"snow_days_30cm":100},
            {"station_id":"BBB","winter":2025,"period":"recent","elev_m":1500,"snow_days_30cm":90}])

    def test_measured_means_and_1500m_boundary(self):
        result=measured_elevation_summary(self.observations()).set_index("elevation_group")
        self.assertEqual(result.loc["below_1500m","n_stations"],1)
        self.assertEqual(result.loc["below_1500m","lost_days"],20)
        self.assertEqual(result.loc["at_least_1500m","lost_days"],10)
        self.assertEqual(result.loc["all_stations","days_past"],80)
        self.assertEqual(result.loc["all_stations","days_recent"],65)
        self.assertEqual(result.loc["all_stations","lost_days"],15)

    def test_missing_measured_period_is_not_zero_loss(self):
        obs=self.observations().iloc[:-1]
        with self.assertRaisesRegex(ValueError,"Both periods"):
            measured_elevation_summary(obs)


if __name__=="__main__":unittest.main()
