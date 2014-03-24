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
        axes_left[i].annotate(
            title, xy=(0, 1), xytext=(0, 5),
            xycoords='axes fraction', textcoords='offset points',
            size='large', color=colors['axes'])
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
        # Set y-axes ticks and labels
        axes_left[i].set_ybound(0, 30)
        axes_left[i].set_yticks(range(0, 31, 5))
        axes_left[i].grid(color=colors['axes'])
        axes_right[i].set_ybound(0, 18)
        axes_right[i].set_yticks(range(0, 19, 3))
        # Add lines at bloom date and actual to ensemble forcing transition
        add_transition_date_line(axes_left[i], data_date, colors)
        add_bloom_date_line(axes_left[i], bloom_dates[member], colors)
    # Set x-axes limits, tick intervals, title, and grid visibility
    set_timeseries_x_limits_ticks_label(
        ax_late, nitrate[prediction['median']], colors)
    hide_ticklabels(ax_early, 'x')
    hide_ticklabels(ax_median, 'x')
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
    ax_left.annotate(
        'Temperature and Salinity', xy=(0, 1), xytext=(0, 5),
        xycoords='axes fraction', textcoords='offset points',
        size='large', color=colors['axes'])
    # Plot time series
    lines, labels = [0]*6, [0]*6
    for i, key in enumerate('early late median'.split()):
        line, = ax_left.plot(
            temperature[prediction[key]].mpl_dates,
            temperature[prediction[key]].dep_data,
            color=colors['temperature_lines'][key])
        lines[i] = line
        labels[i] = key.title()
        line, = ax_right.plot(
            salinity[prediction[key]].mpl_dates,
            salinity[prediction[key]].dep_data,
            color=colors['salinity_lines'][key])
        lines[i + 3] = line
        labels[i + 3] = key.title()
    ax_left.legend(
        lines, labels, title='Forcing Data Source', ncol=2, loc='lower left',
        fancybox=True, framealpha=0.5, fontsize='small')
    # Set x-axes limits, tick intervals, title, and grid visibility
    set_timeseries_x_limits_ticks_label(
        ax_left, temperature[prediction['median']], colors)
    # Set y-axes ticks and labels
    ax_left.set_ybound(4, 18)
    ax_left.grid(color=colors['axes'])
    ax_right.set_ybound(16, 30)
    ax_left.set_ylabel(titles[0], color=colors['temperature'])
    ax_right.set_ylabel(titles[1], color=colors['salinity'])
    # Add line at actual to ensemble forcing transition
    add_transition_date_line(ax_left, data_date, colors)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


def mixing_layer_depth_wind_timeseries(
    mixing_layer_depth, wind, colors, data_date, titles,
):
    fig = matplotlib.figure.Figure(figsize=(15, 4.75), facecolor=colors['bg'])
    ax_left = fig.add_subplot(1, 1, 1)
    ax_right = ax_left.twinx()
    # Set colours of background, spines, ticks, and labels
    ax_left.set_axis_bgcolor(colors['bg'])
    set_spine_and_tick_colors(ax_left, colors, yticks='mld')
    set_spine_and_tick_colors(ax_right, colors, yticks='wind_speed')
    ax_left.annotate(
        'Mixing Layer Depth and Wind Speed', xy=(0, 1), xytext=(0, 5),
        xycoords='axes fraction', textcoords='offset points',
        size='large', color=colors['axes'])

    # Plot time series
    def calc_slice(data):
        slice = np.logical_and(
            data.mpl_dates > matplotlib.dates.date2num(
                data_date.replace(days=-6)),
            data.mpl_dates <= matplotlib.dates.date2num(
                data_date.replace(days=+1)))
        return slice
    mld_slice = calc_slice(mixing_layer_depth)
    mld_dates = mixing_layer_depth.mpl_dates[mld_slice]
    ax_left.fill_between(
        mld_dates, -mixing_layer_depth.dep_data[mld_slice],
        color=colors['mld'], alpha=0.5,
    )
    wind_slice = calc_slice(wind)
    ax_right.fill_between(
        wind.mpl_dates[wind_slice], wind.dep_data[wind_slice],
        color=colors['wind_speed'], alpha=0.25,
    )
    # Set x-axes limits, tick intervals, title, and grid visibility
    ax_left.xaxis.set_major_locator(matplotlib.dates.DayLocator())
    ax_left.xaxis.set_major_formatter(
        matplotlib.dates.DateFormatter('%j\n%d-%b'))
    ax_left.xaxis.set_minor_locator(matplotlib.dates.HourLocator(interval=6))
    ax_left.xaxis.set_tick_params(which='minor', color=colors['axes'])
    start_date = matplotlib.dates.num2date(np.trunc(mld_dates[0]))
    end_date = matplotlib.dates.num2date(np.ceil(mld_dates[-1]))
    ax_left.set_xlim((start_date, end_date))
    if start_date.year == end_date.year:
        label = 'Year-days in {year}'.format(year=start_date.year)
    else:
        label = (
            'Year-days in {first_year} and {second_year}'
            .format(
                first_year=start_date.year,
                second_year=end_date.year))
    ax_left.set_xlabel(label, color=colors['axes'])
    # Set y-axes ticks and labels
    ax_left.set_ybound(-30, 30)
    ax_left.set_yticks(range(-30, 31, 5))
    ax_left.set_yticklabels(
        ('30', '25', '20', '15', '10', '5', '0', '', '', '', '', '', ''))
    ax_left.grid(color=colors['axes'])
    ax_right.set_ybound(-24, 24)
    ax_right.set_yticks(range(-24, 25, 4))
    ax_right.set_yticklabels(
        ('', '', '', '', '', '', '0', '4', '8', '12', '16', '20', '24'))
    ax_left.set_ylabel(titles[0], color=colors['mld'])
    ax_right.set_ylabel(titles[1], color=colors['wind_speed'])
    # Add line to mark profile time
    profile_datetime = matplotlib.dates.date2num(data_date.replace(hours=12))
    ax_left.axvline(profile_datetime, color=colors['axes'])
    ax_left.annotate(
        'Profile Time',
        xy=(profile_datetime, ax_left.get_ylim()[1]),
        xytext=(0, 5), xycoords='data', textcoords='offset points',
        size='small', color=colors['axes'])
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig


def add_bloom_date_line(axes, bloom_date, colors):
    d = datetime.datetime.combine(bloom_date, datetime.time(12))
    axes.axvline(
        matplotlib.dates.date2num(d), color=colors['diatoms'])
    axes.annotate(
        'Bloom Date', xy=(d, axes.get_ylim()[1]), xytext=(2, -12),
        xycoords='data', textcoords='offset points',
        size='small', color=colors['axes'])


def add_transition_date_line(axes, data_date, colors):
    axes.axvline(
        matplotlib.dates.date2num(data_date), color=colors['axes'])
    axes.annotate(
        'Actual to Ensemble\nForcing Transition',
        xy=(matplotlib.dates.date2num(data_date), axes.get_ylim()[1]),
        xytext=(-70, 5), xycoords='data', textcoords='offset points',
        size='small', color=colors['axes'])


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


def set_timeseries_x_limits_ticks_label(axes, timeseries, colors):
    start_date = matplotlib.dates.num2date(np.trunc(timeseries.mpl_dates[0]))
    end_date = matplotlib.dates.num2date(np.ceil(timeseries.mpl_dates[-1]))
    axes.set_xlim((start_date, end_date))
    axes.xaxis.set_major_locator(matplotlib.dates.MonthLocator())
    axes.xaxis.set_major_formatter(
        matplotlib.dates.DateFormatter('%j\n%b'))
    if start_date.year == end_date.year:
        label = 'Year-days in {year}'.format(year=start_date.year)
    else:
        label = (
            'Year-days in {first_year} and {second_year}'
            .format(
                first_year=start_date.year,
                second_year=end_date.year))
    axes.set_xlabel(label, color=colors['axes'])
