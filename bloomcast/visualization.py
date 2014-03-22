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

import matplotlib.backends.backend_agg
import matplotlib.dates
import matplotlib.figure
import numpy as np


def nitrate_diatoms_timeseries(
    nitrate, diatoms, colors, data_date, prediction, bloom_dates, titles,
):
    """Create a time series plot figure object showing nitrate and
    diatom biomass for median and bounds bloom predictions.
    """
    fig = matplotlib.figure.Figure(figsize=(15, 10), facecolor=colors['bg'])
    ax_late = fig.add_subplot(3, 1, 3)
    ax_median = fig.add_subplot(3, 1, 2, sharex=ax_late)
    ax_early = fig.add_subplot(3, 1, 1, sharex=ax_late)
    axes_left = [ax_early, ax_median, ax_late]
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
        axes_left[i].set_title(title, color=colors['axes'])
    # Plot time series
    for i, member in enumerate(prediction.values()):
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
    # Set x-axes limits, tick intervals, title, and grid visibility
    set_timeseries_x_limits_ticks_label(
        ax_late, nitrate[prediction['median']],
        bloom_dates[prediction['median']], colors)
    hide_ticklabels(ax_early, 'x')
    hide_ticklabels(ax_median, 'x')
    # Set y-axes ticks and labels
    for ax in axes_left:
        ax.set_ybound(0, 30)
        ax.set_yticks(range(0, 31, 5))
        ax.grid(color=colors['axes'])
    for ax in axes_right:
        ax.set_ybound(0, 18)
        ax.set_yticks(range(0, 19, 3))
    axes_left[1].set_ylabel(titles[0], color=colors['nitrate'])
    axes_right[1].set_ylabel(titles[1], color=colors['diatoms'])
    return fig


def temperature_salinity_timeseries(
    temperature, salinity, colors, data_date, prediction, bloom_dates, titles,
):
    """Create a time series plot figure object showing temperature
    on the left axis and salinity on the right.
    """
    fig = matplotlib.figure.Figure(figsize=(15, 3.33), facecolor=colors['bg'])
    ax_left = fig.add_subplot(1, 1, 1)
    ax_right = ax_left.twinx()
    # Set colours of background, spines, ticks, and labels
    ax_left.set_axis_bgcolor(colors['bg'])
    set_spine_and_tick_colors(ax_left, colors, yticks='temperature')
    set_spine_and_tick_colors(ax_right, colors, yticks='salinity')
    ax_left.set_title('Temperature and Salinity', color=colors['axes'])
    # Plot time series
    for key, member in prediction.items():
        ax_left.plot(
            temperature[member].mpl_dates,
            temperature[member].dep_data,
            color=colors['temperature_lines'][key])
        ax_right.plot(
            salinity[member].mpl_dates,
            salinity[member].dep_data,
            color=colors['salinity_lines'][key])
    # Add line at actual to ensemble forcing transition
    add_transition_date_line(ax_left, data_date, colors, yloc=18.5)
    # Set x-axes limits, tick intervals, title, and grid visibility
    set_timeseries_x_limits_ticks_label(
        ax_left, temperature[prediction['median']],
        bloom_dates[prediction['median']], colors)
    # Set y-axes ticks and labels
    ax_left.set_ybound(4, 18)
    ax_left.grid(color=colors['axes'])
    ax_right.set_ybound(16, 30)
    ax_left.set_ylabel(titles[0], color=colors['temperature'])
    ax_right.set_ylabel(titles[1], color=colors['salinity'])
    return fig


def mixing_layer_depth_wind_timeseries(
    mixing_layer_depth, wind, colors, data_date, titles,
):
    pass


def add_bloom_date_line(axes, bloom_date, colors):
    d = datetime.datetime.combine(bloom_date, datetime.time(12))
    bloom_date_line = axes.axvline(
        matplotlib.dates.date2num(d), color=colors['diatoms'])
    # Add bloom date line legend
    axes.legend(
        (bloom_date_line,), ('Bloom Date',),
        loc='upper left', fontsize='small')


def add_transition_date_line(axes, data_date, colors, yloc=31):
    axes.axvline(
        matplotlib.dates.date2num(data_date), color=colors['axes'])
    axes.text(
        matplotlib.dates.date2num(data_date), yloc,
        'Actual to Ensemble\nForcing Transition', color=colors['axes'])


def hide_ticklabels(axes, axis='both'):
    if axis in 'x both'.split():
        for t in axes.get_xticklabels():
            t.set_visible(False)
    if axis in 'y both'.split():
        for t in axes.get_yticklabels():
            t.set_visible(False)


def save_as_svg(fig, filename):
    canvas = matplotlib.backends.backend_agg.FigureCanvasAgg(fig)
    canvas.print_svg(filename)


def set_spine_and_tick_colors(axes, colors, yticks):
    for side in 'top bottom left right'.split():
        axes.spines[side].set_color(colors['axes'])
    axes.tick_params(color=colors['axes'])
    for label in axes.get_xticklabels():
        label.set_color(colors['axes'])
    for label in axes.get_yticklabels():
        label.set_color(colors[yticks])


def set_timeseries_x_limits_ticks_label(axes, timeseries, bloom_date, colors):
    axes.set_xlim((
        np.trunc(timeseries.mpl_dates[0]),
        np.ceil(timeseries.mpl_dates[-1]),
    ))
    axes.xaxis.set_major_locator(matplotlib.dates.MonthLocator())
    axes.xaxis.set_major_formatter(
        matplotlib.dates.DateFormatter('%j\n%b'))
    axes.set_xlabel(
        'Year-days in {first_year} and {second_year}'
        .format(
            first_year=bloom_date.year - 1,
            second_year=bloom_date.year,
        ),
        color=colors['axes'])
