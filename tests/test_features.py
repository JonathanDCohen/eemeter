import pandas as pd
import pytest

from eemeter.features import (
    compute_occupancy_feature,
    compute_temperature_features,
    compute_temperature_bin_features,
    compute_time_features,
    compute_usage_per_day_feature,
    estimate_hour_of_week_occupancy,
    get_missing_hours_of_week_warning,
    fit_temperature_bins,
    merge_features,
)
from eemeter.segmentation import segment_time_series


def test_compute_temperature_features_no_freq_index(
    il_electricity_cdd_hdd_billing_monthly
):
    # pick a slice with both hdd and cdd
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    temperature_data.index.freq = None
    with pytest.raises(ValueError):
        compute_temperature_features(meter_data.index, temperature_data)


def test_compute_temperature_features_no_meter_data_tz(
    il_electricity_cdd_hdd_billing_monthly
):
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    meter_data.index = meter_data.index.tz_localize(None)
    with pytest.raises(ValueError):
        compute_temperature_features(meter_data.index, temperature_data)


def test_compute_temperature_features_no_temp_data_tz(
    il_electricity_cdd_hdd_billing_monthly
):
    # pick a slice with both hdd and cdd
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    temperature_data = temperature_data.tz_localize(None)
    with pytest.raises(ValueError):
        compute_temperature_features(meter_data.index, temperature_data)


def test_compute_temperature_features_hourly_temp_mean(il_electricity_cdd_hdd_hourly):
    # pick a slice with both hdd and cdd
    meter_data = il_electricity_cdd_hdd_hourly["meter_data"]["2016-03-01":"2016-07-01"]
    temperature_data = il_electricity_cdd_hdd_hourly["temperature_data"][
        "2016-03-01":"2016-07-01"
    ]
    df = compute_temperature_features(meter_data.index, temperature_data)
    assert list(sorted(df.columns)) == [
        "n_hours_dropped",
        "n_hours_kept",
        "temperature_mean",
    ]
    assert df.shape == (2952, 3)

    assert round(df.temperature_mean.mean()) == 62.0


def test_compute_temperature_features_hourly_hourly_degree_days(
    il_electricity_cdd_hdd_hourly
):
    # pick a slice with both hdd and cdd
    meter_data = il_electricity_cdd_hdd_hourly["meter_data"]["2016-03-01":"2016-07-01"]
    temperature_data = il_electricity_cdd_hdd_hourly["temperature_data"][
        "2016-03-01":"2016-07-01"
    ]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="hourly",
    )
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_hours_dropped",
        "n_hours_kept",
    ]
    assert df.shape == (2952, 6)
    assert round(df.hdd_60.mean(), 2) == 5.25
    assert round(df.hdd_61.mean(), 2) == 5.72
    assert round(df.cdd_65.mean(), 2) == 4.74
    assert round(df.cdd_66.mean(), 2) == 4.33
    assert round(df.n_hours_kept.mean(), 2) == 1.0
    assert round(df.n_hours_dropped.mean(), 2) == 0


def test_compute_temperature_features_hourly_hourly_degree_days_use_mean_false(
    il_electricity_cdd_hdd_hourly
):
    # pick a slice with both hdd and cdd
    meter_data = il_electricity_cdd_hdd_hourly["meter_data"]["2016-03-01":"2016-07-01"]
    temperature_data = il_electricity_cdd_hdd_hourly["temperature_data"][
        "2016-03-01":"2016-07-01"
    ]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="hourly",
        use_mean_daily_values=False,
    )
    assert df.shape == (2952, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_hours_dropped",
        "n_hours_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 0.22
    assert round(df.hdd_61.mean(), 2) == 0.24
    assert round(df.cdd_65.mean(), 2) == 0.2
    assert round(df.cdd_66.mean(), 2) == 0.18
    assert round(df.n_hours_kept.mean(), 2) == 1.0
    assert round(df.n_hours_dropped.mean(), 2) == 0


def test_compute_temperature_features_hourly_daily_degree_days_fail(
    il_electricity_cdd_hdd_hourly
):
    # pick a slice with both hdd and cdd
    meter_data = il_electricity_cdd_hdd_hourly["meter_data"]["2016-03-01":"2016-07-01"]
    temperature_data = il_electricity_cdd_hdd_hourly["temperature_data"][
        "2016-03-01":"2016-07-01"
    ]

    with pytest.raises(ValueError):
        compute_temperature_features(
            meter_data.index,
            temperature_data,
            heating_balance_points=[60, 61],
            cooling_balance_points=[65, 66],
            degree_day_method="daily",
        )


def test_compute_temperature_features_hourly_daily_missing_explicit_freq(
    il_electricity_cdd_hdd_hourly
):
    # pick a slice with both hdd and cdd
    meter_data = il_electricity_cdd_hdd_hourly["meter_data"]["2016-03-01":"2016-07-01"]
    temperature_data = il_electricity_cdd_hdd_hourly["temperature_data"][
        "2016-03-01":"2016-07-01"
    ]

    meter_data.index.freq = None
    with pytest.raises(ValueError):
        compute_temperature_features(
            meter_data.index,
            temperature_data,
            heating_balance_points=[60, 61],
            cooling_balance_points=[65, 66],
            degree_day_method="daily",
        )


def test_compute_temperature_features_hourly_bad_degree_days(
    il_electricity_cdd_hdd_hourly
):
    # pick a slice with both hdd and cdd
    meter_data = il_electricity_cdd_hdd_hourly["meter_data"]["2016-03-01":"2016-07-01"]
    temperature_data = il_electricity_cdd_hdd_hourly["temperature_data"][
        "2016-03-01":"2016-07-01"
    ]

    with pytest.raises(ValueError):
        compute_temperature_features(
            meter_data.index,
            temperature_data,
            heating_balance_points=[60, 61],
            cooling_balance_points=[65, 66],
            degree_day_method="UNKNOWN",
        )


def test_compute_temperature_features_hourly_data_quality(
    il_electricity_cdd_hdd_hourly
):
    # pick a slice with both hdd and cdd
    meter_data = il_electricity_cdd_hdd_hourly["meter_data"]["2016-03-01":"2016-07-01"]
    temperature_data = il_electricity_cdd_hdd_hourly["temperature_data"][
        "2016-03-01":"2016-07-01"
    ]

    df = compute_temperature_features(
        meter_data.index, temperature_data, temperature_mean=False, data_quality=True
    )
    assert df.shape == (2952, 4)
    assert list(sorted(df.columns)) == [
        "n_hours_dropped",
        "n_hours_kept",
        "temperature_not_null",
        "temperature_null",
    ]
    assert round(df.temperature_not_null.mean(), 2) == 1.0
    assert round(df.temperature_null.mean(), 2) == 0.0


def test_compute_temperature_features_daily_temp_mean(il_electricity_cdd_hdd_daily):
    meter_data = il_electricity_cdd_hdd_daily["meter_data"]
    temperature_data = il_electricity_cdd_hdd_daily["temperature_data"]
    df = compute_temperature_features(meter_data.index, temperature_data)
    assert df.shape == (810, 3)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_mean",
    ]

    assert round(df.temperature_mean.mean()) == 55.0


def test_compute_temperature_features_daily_daily_degree_days(
    il_electricity_cdd_hdd_daily
):
    meter_data = il_electricity_cdd_hdd_daily["meter_data"]
    temperature_data = il_electricity_cdd_hdd_daily["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="daily",
    )
    assert df.shape == (810, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_days_dropped",
        "n_days_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 11.05
    assert round(df.hdd_61.mean(), 2) == 11.61
    assert round(df.cdd_65.mean(), 2) == 3.61
    assert round(df.cdd_66.mean(), 2) == 3.25
    assert round(df.n_days_kept.mean(), 2) == 1
    assert round(df.n_days_dropped.mean(), 2) == 0


def test_compute_temperature_features_daily_daily_degree_days_use_mean_false(
    il_electricity_cdd_hdd_daily
):
    meter_data = il_electricity_cdd_hdd_daily["meter_data"]
    temperature_data = il_electricity_cdd_hdd_daily["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="daily",
        use_mean_daily_values=False,
    )
    assert df.shape == (810, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_days_dropped",
        "n_days_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 11.05
    assert round(df.hdd_61.mean(), 2) == 11.61
    assert round(df.cdd_65.mean(), 2) == 3.61
    assert round(df.cdd_66.mean(), 2) == 3.25
    assert round(df.n_days_kept.mean(), 2) == 1
    assert round(df.n_days_dropped.mean(), 2) == 0


def test_compute_temperature_features_daily_hourly_degree_days(
    il_electricity_cdd_hdd_daily
):
    meter_data = il_electricity_cdd_hdd_daily["meter_data"]
    temperature_data = il_electricity_cdd_hdd_daily["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="hourly",
    )
    assert df.shape == (810, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_hours_dropped",
        "n_hours_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 11.48
    assert round(df.hdd_61.mean(), 2) == 12.06
    assert round(df.cdd_65.mean(), 2) == 4.04
    assert round(df.cdd_66.mean(), 2) == 3.69
    assert round(df.n_hours_kept.mean(), 2) == 23.97
    assert round(df.n_hours_dropped.mean(), 2) == 0


def test_compute_temperature_features_daily_hourly_degree_days_use_mean_false(
    il_electricity_cdd_hdd_daily
):
    meter_data = il_electricity_cdd_hdd_daily["meter_data"]
    temperature_data = il_electricity_cdd_hdd_daily["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="hourly",
        use_mean_daily_values=False,
    )
    assert df.shape == (810, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_hours_dropped",
        "n_hours_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 11.43
    assert round(df.hdd_61.mean(), 2) == 12.01
    assert round(df.cdd_65.mean(), 2) == 4.04
    assert round(df.cdd_66.mean(), 2) == 3.69
    assert round(df.n_hours_kept.mean(), 2) == 23.97
    assert round(df.n_hours_dropped.mean(), 2) == 0


def test_compute_temperature_features_daily_bad_degree_days(
    il_electricity_cdd_hdd_daily
):
    meter_data = il_electricity_cdd_hdd_daily["meter_data"]
    temperature_data = il_electricity_cdd_hdd_daily["temperature_data"]
    with pytest.raises(ValueError):
        compute_temperature_features(
            meter_data.index,
            temperature_data,
            heating_balance_points=[60, 61],
            cooling_balance_points=[65, 66],
            degree_day_method="UNKNOWN",
        )


def test_compute_temperature_features_daily_data_quality(il_electricity_cdd_hdd_daily):
    meter_data = il_electricity_cdd_hdd_daily["meter_data"]
    temperature_data = il_electricity_cdd_hdd_daily["temperature_data"]
    df = compute_temperature_features(
        meter_data.index, temperature_data, temperature_mean=False, data_quality=True
    )
    assert df.shape == (810, 4)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_not_null",
        "temperature_null",
    ]
    assert round(df.temperature_not_null.mean(), 2) == 23.97
    assert round(df.temperature_null.mean(), 2) == 0.00


def test_compute_temperature_features_billing_monthly_temp_mean(
    il_electricity_cdd_hdd_billing_monthly
):
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    df = compute_temperature_features(meter_data.index, temperature_data)
    assert df.shape == (27, 3)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_mean",
    ]
    assert round(df.temperature_mean.mean()) == 54.0


def test_compute_temperature_features_billing_monthly_daily_degree_days(
    il_electricity_cdd_hdd_billing_monthly
):
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="daily",
    )
    assert df.shape == (27, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_days_dropped",
        "n_days_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 11.42
    assert round(df.hdd_61.mean(), 2) == 12.0
    assert round(df.cdd_65.mean(), 2) == 3.54
    assert round(df.cdd_66.mean(), 2) == 3.19
    assert round(df.n_days_kept.mean(), 2) == 29.96
    assert round(df.n_days_dropped.mean(), 2) == 0.04


def test_compute_temperature_features_billing_monthly_daily_degree_days_use_mean_false(
    il_electricity_cdd_hdd_billing_monthly
):
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="daily",
        use_mean_daily_values=False,
    )
    assert df.shape == (27, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_days_dropped",
        "n_days_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 332.23
    assert round(df.hdd_61.mean(), 2) == 349.34
    assert round(df.cdd_65.mean(), 2) == 108.42
    assert round(df.cdd_66.mean(), 2) == 97.58
    assert round(df.n_days_kept.mean(), 2) == 29.96
    assert round(df.n_days_dropped.mean(), 2) == 0.04


def test_compute_temperature_features_billing_monthly_hourly_degree_days(
    il_electricity_cdd_hdd_billing_monthly
):
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="hourly",
    )
    assert df.shape == (27, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_hours_dropped",
        "n_hours_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 11.8
    assert round(df.hdd_61.mean(), 2) == 12.38
    assert round(df.cdd_65.mean(), 2) == 3.96
    assert round(df.cdd_66.mean(), 2) == 3.62
    assert round(df.n_hours_kept.mean(), 2) == 719.15
    assert round(df.n_hours_dropped.mean(), 2) == 0


def test_compute_temperature_features_billing_monthly_hourly_degree_days_use_mean_false(
    il_electricity_cdd_hdd_billing_monthly
):
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="hourly",
        use_mean_daily_values=False,
    )
    assert df.shape == (27, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_hours_dropped",
        "n_hours_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 343.01
    assert round(df.hdd_61.mean(), 2) == 360.19
    assert round(df.cdd_65.mean(), 2) == 121.29
    assert round(df.cdd_66.mean(), 2) == 110.83
    assert round(df.n_hours_kept.mean(), 2) == 719.15
    assert round(df.n_hours_dropped.mean(), 2) == 0


def test_compute_temperature_features_billing_monthly_bad_degree_day_method(
    il_electricity_cdd_hdd_billing_monthly
):
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    with pytest.raises(ValueError):
        compute_temperature_features(
            meter_data.index,
            temperature_data,
            heating_balance_points=[60, 61],
            cooling_balance_points=[65, 66],
            degree_day_method="UNKNOWN",
        )


def test_compute_temperature_features_billing_monthly_data_quality(
    il_electricity_cdd_hdd_billing_monthly
):
    meter_data = il_electricity_cdd_hdd_billing_monthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_monthly["temperature_data"]
    df = compute_temperature_features(
        meter_data.index, temperature_data, temperature_mean=False, data_quality=True
    )
    assert df.shape == (27, 4)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_not_null",
        "temperature_null",
    ]
    assert round(df.temperature_not_null.mean(), 2) == 719.15
    assert round(df.temperature_null.mean(), 2) == 0.0


def test_compute_temperature_features_billing_bimonthly_temp_mean(
    il_electricity_cdd_hdd_billing_bimonthly
):
    meter_data = il_electricity_cdd_hdd_billing_bimonthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_bimonthly["temperature_data"]
    df = compute_temperature_features(meter_data.index, temperature_data)
    assert df.shape == (14, 3)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_mean",
    ]
    assert round(df.temperature_mean.mean()) == 53.0


def test_compute_temperature_features_billing_bimonthly_daily_degree_days(
    il_electricity_cdd_hdd_billing_bimonthly
):
    meter_data = il_electricity_cdd_hdd_billing_bimonthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_bimonthly["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="daily",
    )
    assert df.shape == (14, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_days_dropped",
        "n_days_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 12.72
    assert round(df.hdd_61.mean(), 2) == 13.32
    assert round(df.cdd_65.mean(), 2) == 3.39
    assert round(df.cdd_66.mean(), 2) == 3.05
    assert round(df.n_days_kept.mean(), 2) == 57.79
    assert round(df.n_days_dropped.mean(), 2) == 0.07


def test_compute_temperature_features_billing_bimonthly_hourly_degree_days(
    il_electricity_cdd_hdd_billing_bimonthly
):
    meter_data = il_electricity_cdd_hdd_billing_bimonthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_bimonthly["temperature_data"]
    df = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[60, 61],
        cooling_balance_points=[65, 66],
        temperature_mean=False,
        degree_day_method="hourly",
    )
    assert df.shape == (14, 6)
    assert list(sorted(df.columns)) == [
        "cdd_65",
        "cdd_66",
        "hdd_60",
        "hdd_61",
        "n_hours_dropped",
        "n_hours_kept",
    ]
    assert round(df.hdd_60.mean(), 2) == 13.08
    assert round(df.hdd_61.mean(), 2) == 13.69
    assert round(df.cdd_65.mean(), 2) == 3.78
    assert round(df.cdd_66.mean(), 2) == 3.46
    assert round(df.n_hours_kept.mean(), 2) == 1386.93
    assert round(df.n_hours_dropped.mean(), 2) == 0


def test_compute_temperature_features_billing_bimonthly_bad_degree_days(
    il_electricity_cdd_hdd_billing_bimonthly
):
    meter_data = il_electricity_cdd_hdd_billing_bimonthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_bimonthly["temperature_data"]
    with pytest.raises(ValueError):
        compute_temperature_features(
            meter_data.index,
            temperature_data,
            heating_balance_points=[60, 61],
            cooling_balance_points=[65, 66],
            degree_day_method="UNKNOWN",
        )


def test_compute_temperature_features_billing_bimonthly_data_quality(
    il_electricity_cdd_hdd_billing_bimonthly
):
    meter_data = il_electricity_cdd_hdd_billing_bimonthly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_billing_bimonthly["temperature_data"]
    df = compute_temperature_features(
        meter_data.index, temperature_data, temperature_mean=False, data_quality=True
    )
    assert df.shape == (14, 4)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_not_null",
        "temperature_null",
    ]
    assert round(df.temperature_not_null.mean(), 2) == 1386.93
    assert round(df.temperature_null.mean(), 2) == 0.0


def test_compute_temperature_features_shorter_temperature_data(
    il_electricity_cdd_hdd_daily
):
    meter_data = il_electricity_cdd_hdd_daily["meter_data"]
    temperature_data = il_electricity_cdd_hdd_daily["temperature_data"]

    # drop some data
    temperature_data = temperature_data[:-200]

    df = compute_temperature_features(meter_data.index, temperature_data)
    assert df.shape == (810, 3)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_mean",
    ]
    assert round(df.temperature_mean.sum()) == 43958.0


def test_compute_temperature_features_shorter_meter_data(il_electricity_cdd_hdd_daily):
    meter_data = il_electricity_cdd_hdd_daily["meter_data"]
    temperature_data = il_electricity_cdd_hdd_daily["temperature_data"]

    # drop some data
    meter_data = meter_data[:-10]

    df = compute_temperature_features(meter_data.index, temperature_data)
    assert df.shape == (800, 3)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_mean",
    ]
    assert round(df.temperature_mean.sum()) == 43934.0


def test_compute_temperature_features_empty_temperature_data():
    index = pd.DatetimeIndex([], tz="UTC", name="dt", freq="H")
    temperature_data = pd.Series({"value": []}, index=index).astype(float)
    result_index = temperature_data.resample("D").sum().index
    meter_data_hack = pd.DataFrame({"value": 0}, index=result_index)

    df = compute_temperature_features(
        meter_data_hack.index,
        temperature_data,
        heating_balance_points=[65],
        cooling_balance_points=[65],
        degree_day_method="daily",
        use_mean_daily_values=False,
    )
    assert df.shape == (0, 3)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_mean",
    ]
    assert round(df.temperature_mean.sum()) == 0


def test_compute_temperature_features_empty_meter_data():
    index = pd.DatetimeIndex([], tz="UTC", name="dt", freq="H")
    temperature_data = pd.Series({"value": 0}, index=index)
    result_index = temperature_data.resample("D").sum().index
    meter_data_hack = pd.DataFrame({"value": []}, index=result_index)
    meter_data_hack.index.freq = None

    df = compute_temperature_features(
        meter_data_hack.index,
        temperature_data,
        heating_balance_points=[65],
        cooling_balance_points=[65],
        degree_day_method="daily",
        use_mean_daily_values=False,
    )
    assert df.shape == (0, 3)
    assert list(sorted(df.columns)) == [
        "n_days_dropped",
        "n_days_kept",
        "temperature_mean",
    ]
    assert round(df.temperature_mean.sum()) == 0


def test_merge_features():
    index = pd.date_range("2017-01-01", periods=100, freq="H", tz="UTC")
    features = merge_features(
        [
            pd.Series(1, index=index, name="a"),
            pd.DataFrame({"b": 2}, index=index),
            pd.DataFrame({"c": 3, "d": 4}, index=index),
        ]
    )
    assert list(features.columns) == ["a", "b", "c", "d"]
    assert features.shape == (100, 4)
    assert features.sum().sum() == 1000
    assert features.a.sum() == 100
    assert features.b.sum() == 200
    assert features.c.sum() == 300
    assert features.d.sum() == 400
    assert features.index[0] == index[0]
    assert features.index[-1] == index[-1]


def test_merge_features_empty_raises():
    with pytest.raises(ValueError):
        features = merge_features([])


@pytest.fixture
def meter_data_hourly():
    index = pd.date_range("2017-01-01", periods=100, freq="H", tz="UTC")
    return pd.DataFrame({"value": 1}, index=index)


def test_compute_usage_per_day_feature_hourly(meter_data_hourly):
    usage_per_day = compute_usage_per_day_feature(meter_data_hourly)
    assert usage_per_day.name == "usage_per_day"
    assert usage_per_day["2017-01-01T00:00:00Z"] == 24
    assert usage_per_day.sum() == 2376.0


def test_compute_usage_per_day_feature_hourly_series_name(meter_data_hourly):
    usage_per_day = compute_usage_per_day_feature(
        meter_data_hourly, series_name="meter_value"
    )
    assert usage_per_day.name == "meter_value"


@pytest.fixture
def meter_data_daily():
    index = pd.date_range("2017-01-01", periods=100, freq="D", tz="UTC")
    return pd.DataFrame({"value": 1}, index=index)


def test_compute_usage_per_day_feature_daily(meter_data_daily):
    usage_per_day = compute_usage_per_day_feature(meter_data_daily)
    assert usage_per_day["2017-01-01T00:00:00Z"] == 1
    assert usage_per_day.sum() == 99.0


@pytest.fixture
def meter_data_billing():
    index = pd.date_range("2017-01-01", periods=100, freq="MS", tz="UTC")
    return pd.DataFrame({"value": 1}, index=index)


def test_compute_usage_per_day_feature_billing(meter_data_billing):
    usage_per_day = compute_usage_per_day_feature(meter_data_billing)
    assert usage_per_day["2017-01-01T00:00:00Z"] == 1. / 31
    assert usage_per_day.sum().round(3) == 3.257


@pytest.fixture
def complete_hour_of_week_feature():
    index = pd.date_range("2017-01-01", periods=168, freq="H", tz="UTC")
    time_features = compute_time_features(index, hour_of_week=True)
    hour_of_week_feature = time_features.hour_of_week
    return hour_of_week_feature


def test_get_missing_hours_of_week_warning_ok(complete_hour_of_week_feature):
    warning = get_missing_hours_of_week_warning(complete_hour_of_week_feature)
    assert warning is None


@pytest.fixture
def partial_hour_of_week_feature():
    index = pd.date_range("2017-01-01", periods=84, freq="H", tz="UTC")
    time_features = compute_time_features(index, hour_of_week=True)
    hour_of_week_feature = time_features.hour_of_week
    return hour_of_week_feature


def test_get_missing_hours_of_week_warning_triggered(partial_hour_of_week_feature):
    warning = get_missing_hours_of_week_warning(partial_hour_of_week_feature)
    assert warning.qualified_name is not None
    assert warning.description is not None
    assert warning.data["missing_hours_of_week"] == list(range(60, 144))


def test_compute_time_features_bad_freq():
    index = pd.date_range("2017-01-01", periods=168, freq="D", tz="UTC")
    with pytest.raises(ValueError):
        compute_time_features(index)


def test_compute_time_features_all():
    index = pd.date_range("2017-01-01", periods=168, freq="H", tz="UTC")
    features = compute_time_features(index)
    assert list(features.columns) == ["day_of_week", "hour_of_day", "hour_of_week"]
    assert features.shape == (168, 3)
    assert features.sum().sum() == 16464.0
    with pytest.raises(TypeError):  # categoricals
        features.day_of_week.sum()
    with pytest.raises(TypeError):
        features.hour_of_day.sum()
    with pytest.raises(TypeError):
        features.hour_of_week.sum()
    assert features.day_of_week.astype("float").sum() == sum(range(7)) * 24
    assert features.hour_of_day.astype("float").sum() == sum(range(24)) * 7
    assert features.hour_of_week.astype("float").sum() == sum(range(168))
    assert features.index[0] == index[0]
    assert features.index[-1] == index[-1]


def test_compute_time_features_none():
    index = pd.date_range("2017-01-01", periods=168, freq="H", tz="UTC")
    with pytest.raises(ValueError):
        compute_time_features(
            index, hour_of_week=False, day_of_week=False, hour_of_day=False
        )


@pytest.fixture
def occupancy_precursor(il_electricity_cdd_hdd_hourly):
    meter_data = il_electricity_cdd_hdd_hourly["meter_data"]
    temperature_data = il_electricity_cdd_hdd_hourly["temperature_data"]
    time_features = compute_time_features(meter_data.index)
    temperature_features = compute_temperature_features(
        meter_data.index,
        temperature_data,
        heating_balance_points=[50],
        cooling_balance_points=[65],
        degree_day_method="hourly",
    )
    return merge_features(
        [meter_data.value.to_frame("meter_value"), temperature_features, time_features]
    )


def test_estimate_hour_of_week_occupancy_no_segmentation(occupancy_precursor):
    occupancy = estimate_hour_of_week_occupancy(occupancy_precursor)
    assert list(occupancy.columns) == ["occupancy"]
    assert occupancy.shape == (168, 1)
    assert occupancy.sum().sum() == 0


@pytest.fixture
def one_month_segmentation(occupancy_precursor):
    return segment_time_series(occupancy_precursor.index, segment_type="one_month")


def test_estimate_hour_of_week_occupancy_one_month_segmentation(
    occupancy_precursor, one_month_segmentation
):
    occupancy = estimate_hour_of_week_occupancy(
        occupancy_precursor, segmentation=one_month_segmentation
    )
    assert list(occupancy.columns) == [
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]
    assert occupancy.shape == (168, 12)
    assert occupancy.sum().sum() == 82.0


@pytest.fixture
def temperature_means():
    index = pd.date_range("2017-01-01", periods=2000, freq="H", tz="UTC")
    return pd.DataFrame({"temperature_mean": [10, 35, 55, 80, 100] * 400}, index=index)


def test_fit_temperature_bins_no_segmentation(temperature_means):
    bins = fit_temperature_bins(temperature_means, segmentation=None)
    assert list(bins.columns) == ["keep_bin_endpoint"]
    assert bins.shape == (6, 1)
    assert bins.sum().sum() == 4


def test_fit_temperature_bins_one_month_segmentation(
    temperature_means, one_month_segmentation
):
    bins = fit_temperature_bins(temperature_means, segmentation=one_month_segmentation)
    assert list(bins.columns) == [
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]
    assert bins.shape == (6, 12)
    assert bins.sum().sum() == 12


def test_compute_temperature_bin_features(temperature_means):
    temps = temperature_means.temperature_mean
    bin_features = compute_temperature_bin_features(temps, [25, 75])
    assert list(bin_features.columns) == ["bin_0", "bin_1", "bin_2"]
    assert bin_features.shape == (2000, 3)
    assert bin_features.sum().sum() == 112000.0


@pytest.fixture
def even_occupancy():
    return pd.Series([i % 2 == 0 for i in range(168)], index=pd.Categorical(range(168)))


def test_compute_occupancy_feature(even_occupancy):
    index = pd.date_range("2017-01-01", periods=1000, freq="H", tz="UTC")
    time_features = compute_time_features(index, hour_of_week=True)
    hour_of_week = time_features.hour_of_week
    occupancy = compute_occupancy_feature(hour_of_week, even_occupancy)
    assert occupancy.name == "occupancy"
    assert occupancy.shape == (1000,)
    assert occupancy.sum().sum() == 500
