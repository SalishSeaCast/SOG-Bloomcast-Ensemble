# Copyright 2011-2014 Doug Latornell and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Results visualization functions for SoG-bloomcast.
"""
import datetime

import matplotlib.dates
import matplotlib.pyplot as plt
import numpy as np


def nitrate_diatoms_timeseries(
    nitrate, diatoms, colors, data_date, prediction, bloom_dates, titles,
):
    """Create a time series plot figure object showing nitrate and
    diatom biomass for median and bounds bloom predictions.
    """
    fig, axes_left = plt.subplots(
        3, 1, figsize=(15, 10), facecolor=colors['bg'], sharex=True)
    axes_right = [ax.twinx() for ax in axes_left]
    # Set colours of background, spines, ticks, and labels
    for ax in axes_left:
        ax.set_axis_bgcolor(colors['bg'])
        set_spine_and_tick_colors(ax, colors, yticks='nitrate')
    for ax in axes_right:
        set_spine_and_tick_colors(ax, colors, yticks='diatoms')
    # Set titles above each sub-plot
    ax_titles = (
        'Early Bound Prediction',
        'Median Prediction',
        'Late Bound Prediction',
    )
    for i, title in enumerate(ax_titles):
        axes_left[i].set_title(title, color=colors['axes'], loc='left')
    # Plot time series
    axes_keys = (
        prediction['early'],
        prediction['median'],
        prediction['late'],
    )
    for i, member in enumerate(axes_keys):
        axes_left[i].plot(
            nitrate[member].mpl_dates,
            nitrate[member].dep_data,
            color=colors['nitrate'],
        )
        axes_right[i].plot(
            diatoms[member].mpl_dates,
            diatoms[member].dep_data,
            color=colors['diatoms'],
        )
        # Add lines at bloom date and actual to ensemble forcing transition
        add_transition_date_line(axes_left[i], data_date, colors)
        add_bloom_date_line(axes_left[i], bloom_dates[member], colors)
    # Set axes limits, tick intervals, and grid visibility
    set_timeseries_x_limits_ticks_label(
        axes_left[2], nitrate[prediction['median']], colors)
    for ax in axes_left:
        ax.set_yticks(range(0, 31, 5))
        ax.grid(color=colors['axes'])
    for ax in axes_right:
        ax.set_yticks(range(0, 19, 3))
    # Set axes labels
    axes_left[1].set_ylabel(titles[0], color=colors['nitrate'])
    axes_right[1].set_ylabel(titles[1], color=colors['diatoms'])
    return fig


def two_axis_timeseries(
    left_ts, right_ts, colors, titles, data_date, bloom_dates,
):
    """Create a time series plot figure object showing 2 time series with
    left and right axes.
    """
    fig, ax_left = plt.subplots(1, 1, figsize=(8, 3), facecolor=colors['bg'])
    ax_right = ax_left.twinx()
    # Set colours of background, spines, ticks, and labels
    ax_left.set_axis_bgcolor(colors['bg'])
    set_spine_and_tick_colors(ax_left, colors, yticks='temperature')
    set_spine_and_tick_colors(ax_right, colors, yticks='salinity')
    return fig


def mixing_layer_depth_wind_timeseries(
    mixing_layer_depth, wind, colors, data_date, titles,
):
    pass


def set_spine_and_tick_colors(axis, colors, yticks):
    for side in 'top bottom left right'.split():
        axis.spines[side].set_color(colors['axes'])
    axis.tick_params(color=colors['axes'])
    for label in axis.get_xticklabels():
        label.set_color(colors['axes'])
    for label in axis.get_yticklabels():
        label.set_color(colors[yticks])


def add_transition_date_line(axis, data_date, colors, yloc=31):
    axis.axvline(
        matplotlib.dates.date2num(data_date), color=colors['axes'])
    axis.text(
        matplotlib.dates.date2num(data_date), yloc,
        'Actual to Ensemble\nForcing Transition', color=colors['axes'])


def add_bloom_date_line(axis, bloom_date, colors):
    d = datetime.datetime.combine(bloom_date, datetime.time(12))
    bloom_date_line = axis.axvline(
        matplotlib.dates.date2num(d), color=colors['diatoms'])
    # Add bloom date line legend
    axis.legend(
        (bloom_date_line,), ('Bloom Date',),
        loc='upper left', fontsize='small')


def set_timeseries_x_limits_ticks_label(axis, timeseries, colors):
    axis.set_xlim((
        np.trunc(timeseries.mpl_dates[0]),
        np.ceil(timeseries.mpl_dates[-1]),
    ))
    axis.xaxis.set_major_locator(matplotlib.dates.MonthLocator())
    axis.xaxis.set_major_formatter(
        matplotlib.dates.DateFormatter('%j\n%b'))
    axis.set_xlabel('Year-days in 2103 and 2014', color=colors['axes'])
