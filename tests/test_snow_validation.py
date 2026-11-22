"""Checks for time matching, missing data, joins and independent error arithmetic."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from snow_validation import season_dates, summarize_hourly, pair_sources, compute_results


class SnowValidationTests(unittest.TestCase):
    def payload(self, year=1996):
        dates = season_dates(year)
        hours = pd.date_range(dates[0], dates[-1]+pd.Timedelta(hours=23), freq="h")
        return {"hourly_units":{"snow_depth":"m"}, "utc_offset_seconds":0,
                "latitude":46.0,"longitude":8.0,
                "hourly":{"time":hours.strftime("%Y-%m-%dT%H:%M").tolist(),"snow_depth":[0.0]*len(hours)}}

    def test_boundary_time_and_leap_day(self):
        data=self.payload()
        data["hourly"]["snow_depth"][6]=.30
        data["hourly"]["snow_depth"][24+6]=.29
        data["hourly"]["snow_depth"][24+12]=.30
        data["hourly"]["snow_depth"][-1]=.30
        result=summarize_hourly(data,1996)
        self.assertEqual(result["model_observed_days"],137)
        self.assertEqual(result["model_days_06utc"],1)
        self.assertEqual(result["model_days_daily_max"],3)

    def test_missing_hour_is_not_zero_snow(self):
        data=self.payload()
        data["hourly"]["time"].pop(100)
        data["hourly"]["snow_depth"].pop(100)
        with self.assertRaisesRegex(ValueError,"missing, irregular"):
            summarize_hourly(data,1996)

    def test_missing_depth_is_not_zero_snow(self):
        data=self.payload()
        data["hourly"]["snow_depth"][100]=None
        with self.assertRaises(ValueError):summarize_hourly(data,1996)

    def test_unit_mismatch_rejected(self):
        data=self.payload();data["hourly_units"]["snow_depth"]="cm"
        with self.assertRaisesRegex(ValueError,"metres"):
            summarize_hourly(data,1996)

    def pair(self):
        obs=pd.DataFrame([{"station_id":"AAA","winter":1995,"period":"past","snow_days_30cm":63,
                           "observed_days":136,"elev_m":1321}])
        model=pd.DataFrame([{"station_id":"AAA","winter":1995,"period":"past","model_days_06utc":121,
                             "model_days_daily_max":122,"model_observed_days":136,"model_hours":3264,"query_elev_m":1321}])
        return obs,model

    def test_pair_error_sign(self):
        obs,model=self.pair()
        result=pair_sources(obs,model)
        self.assertEqual(result.error_days.iloc[0],58)
        self.assertEqual(result.daily_max_extra_days.iloc[0],1)

    def test_wrong_winter_and_duplicate_keys_rejected(self):
        obs,model=self.pair()
        with self.assertRaises(ValueError):pair_sources(obs,pd.concat([model,model]))
        model.loc[0,"winter"]=2025
        with self.assertRaises(ValueError):pair_sources(obs,model)

    def test_station_elevation_mismatch_rejected(self):
        obs,model=self.pair();model.loc[0,"query_elev_m"]=2000
        with self.assertRaisesRegex(ValueError,"elevations"):
            pair_sources(obs,model)

    def test_wrong_requested_coordinates_rejected(self):
        obs,model=self.pair()
        obs["lat"]=46.;obs["lon"]=8.
        model["request_url"]="https://archive-api.open-meteo.com/v1/archive?latitude=47&longitude=8&elevation=1321&start_date=1994-12-01&end_date=1995-04-15&hourly=snow_depth&models=era5_land&timezone=GMT&cell_selection=land"
        with self.assertRaisesRegex(ValueError,"coordinates"):
            pair_sources(obs,model)

    def test_metrics_and_period_difference_arithmetic(self):
        rows=[]
        # Observed losses are 20 and -10; model losses 10 and -20.
        for station,obs,model in [("AAA",(80,60),(100,90)),("BBB",(30,40),(50,70))]:
            for year,period,i in [(1995,"past",0),(2025,"recent",1)]:
                rows.append({"station_id":station,"station_name":station,"lat":46.,"lon":8.,"elev_m":1500,
                             "winter":year,"period":period,"observed_days_06utc":obs[i],"model_days_06utc":model[i],
                             "observed_days":136,"daily_max_extra_days":0,"error_days":model[i]-obs[i]})
        metrics,changes,trend=compute_results(pd.DataFrame(rows))
        all_rows=metrics.loc[metrics.period.eq("all")].iloc[0]
        self.assertAlmostEqual(all_rows.bias_days,25)
        self.assertAlmostEqual(all_rows.rmse_days,np.sqrt(650))
        self.assertAlmostEqual(trend.mean_observed_lost_days.iloc[0],5)
        self.assertAlmostEqual(trend.mean_model_lost_days.iloc[0],-5)
        self.assertAlmostEqual(trend.mean_loss_error_days.iloc[0],-10)


if __name__=="__main__":unittest.main()
