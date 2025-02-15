# Copyright 2011-2021 Doug Latornell and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Driver module for SoG-bloomcast project"""
from copy import copy
import datetime
import logging
import logging.handlers
import math
import os
import subprocess
import sys
import time
import arrow
import numpy as np
from matplotlib.dates import (
    date2num,
    DateFormatter,
    DayLocator,
    HourLocator,
    MonthLocator,
)
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import SOGcommand
from .meteo import MeteoProcessor
from .rivers import RiversProcessor
from .utils import (
    Config,
    SOG_HoffmuellerProfile,
    SOG_Timeseries,
)
from .wind import WindProcessor

# Bloom peak identification parameters based on:

#   Allen & Wolfe, 2013 [1]:

#   "Although the idea of a spring bloom is well-defined, the exact
#   timing of a real spring bloom is not.
#   In Collins, et al, 2009 [2] the peak of the bloom was defined as the
#   highest concentration of phytoplankton unless an earlier bloom
#   (more than 5 days earlier) was associated with nitrate going to zero.
#   Gower, et al, 2013 [3],
#   using satellite data,
#   chooses a measure of the start of the bloom as the time when the
#   whole Strait of Georgia has high chlorophyll.
#   The nutritional quality of the phytoplankton appears to change when
#   they become nutrient limited Sastri & Dower, 2009 [4].
#   Thus here we use a definition that should delineate between nutrient
#   replete spring conditions and nutrient stressed summer conditions.
#   We use the peak phytoplankton concentration
#   (averaged from the surface to 3 m depth)
#   within four days of the average 0-3 m nitrate concentration going
#   below 0.5 uM (the half-saturation concentration) for two consecutive
#   days."

# [1] Allen, S. E. and M. A. Wolfe,
# Hindcast of the Timing of the Spring Phytoplankton Bloom in the Strait
# of Georgia, 1968-2010.
# Progress in Oceanography, vol 115 (2013), pp. 6-13.
# http://dx.doi.org/10.1016/j.pocean.2013.05.026

# [2] A.K. Collins, S.E. Allen, R. Pawlowicz,
# The role of wind in determining the timing of the spring bloom in the
# Strait of Georgia.
# Canadian Journal of Fisheries and Aquatic Sciences, 66 (2009),
# pp. 1597–1616.
# http://dx.doi.org/10.1139/F09-071

# [3] Gower, J., King, S., Statham, S., Fox, R., Young, E.,
# The Malaspina Dragon: a new pattern of the early spring bloom in the
# Strait of Georgia.
# Progress in Oceanography 115 (2013), pp. 181–188.
# http://dx.doi.org/10.1016/j.pocean.2013.05.024

# [4] A.R. Sastri and J.F. Dower,
# Interannual variability in chitobiase-based production rates of the
# crustacean zooplankton community in the Strait of Georgia,
# British Columbia, Canada.
# Marine Ecology-Progress Series, 388 (2009), pp. 147–157.
# http://dx.doi.org/10.3354/meps08111
NITRATE_HALF_SATURATION_CONCENTRATION = 0.5  # uM
PHYTOPLANKTON_PEAK_WINDOW_HALF_WIDTH = 4  # days


log = logging.getLogger("bloomcast")
bloom_date_log = logging.getLogger("bloomcast.bloom_date")


class NoNewWindData(Exception):
    pass


class Bloomcast(object):
    """Strait of Georgia spring diatom bloom predictor.

    :arg config_file: Path for the bloomcast configuration file.
    :type config_file: string
    """

    # Colours for graph lines
    nitrate_colours = {"avg": "#30b8b8", "bounds": "#82dcdc"}
    diatoms_colours = {"avg": "green", "bounds": "#56c056"}
    temperature_colours = {"avg": "red", "bounds": "#ff7373"}
    salinity_colours = {"avg": "blue", "bounds": "#7373ff"}

    def __init__(self, config_file, data_date):
        self.config = Config()
        self.config.load_config(config_file)
        # Wind data date for development and debugging; overwritten if
        # wind forcing data is collected and processed
        self.config.data_date = data_date

    def run(self):
        """Execute the bloomcast prediction and report its results.

        * Load the process configuration data.

        * Get the wind forcing data.

        * Get the meteorological and river flow forcing data.

        * Run the SOG code.

        * Calculate the spring diatom bloom date.
        """
        self._configure_logging()
        if not self.config.get_forcing_data and self.config.data_date is None:
            log.debug(
                "This will not end well: "
                "get_forcing_data={0.get_forcing_data} "
                "and data_date={0.data_date}".format(self.config)
            )
            return
        log.debug(
            "run start date/time is {0:%Y-%m-%d %H:%M:%S}".format(
                self.config.run_start_date
            )
        )
        # Check run start date and current date to ensure that
        # river flow data are available.
        # River flow data are only available in a rolling 18-month window.
        run_start_yr_jan1 = arrow.get(self.config.run_start_date).replace(
            month=1, day=1
        )
        river_date_limit = arrow.now().replace(months=-18)
        if run_start_yr_jan1 < river_date_limit:
            log.error(
                "A bloomcast run starting {0.run_start_date:%Y-%m-%d} cannot "
                "be done today because there are no river flow data availble "
                "prior to {1}".format(
                    self.config, river_date_limit.format("YYYY-MM-DD")
                )
            )
            return
        try:
            self._get_forcing_data()
        except NoNewWindData:
            log.info(
                "Wind data date {0:%Y-%m-%d} is unchanged since last run".format(
                    self.config.data_date
                )
            )
            return
        self._run_SOG()
        self._get_results_timeseries()
        self._create_timeseries_graphs()
        self._get_results_profiles()
        self._create_profile_graphs()
        self._calc_bloom_date()

    def _configure_logging(self):
        """Configure logging of debug & warning messages to console
        and email.

        Debug logging on/off & email recipient(s) for warning messages
        are set in config file.
        """
        log.setLevel(logging.DEBUG)

        def patched_data_filter(record):
            if record.funcName == "patch_data" and "data patched" in record.msg:
                return 0
            return 1

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        console.setLevel(logging.INFO)
        if self.config.logging.debug:
            console.setLevel(logging.DEBUG)
        console.addFilter(patched_data_filter)
        log.addHandler(console)

        disk = logging.handlers.RotatingFileHandler(
            self.config.logging.bloomcast_log_filename, maxBytes=1024 * 1024
        )
        disk.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M",
            )
        )
        disk.setLevel(logging.DEBUG)
        log.addHandler(disk)

        mailhost = (
            ("localhost", 1025)
            if self.config.logging.use_test_smtpd
            else "smtp.eos.ubc.ca"
        )
        email = logging.handlers.SMTPHandler(
            mailhost,
            fromaddr="SoG-bloomcast@eos.ubc.ca",
            toaddrs=self.config.logging.toaddrs,
            subject="Warning Message from SoG-bloomcast",
            timeout=10.0,
        )
        email.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        email.setLevel(logging.WARNING)
        log.addHandler(email)

        bloom_date_evolution = logging.FileHandler(
            self.config.logging.bloom_date_log_filename
        )
        bloom_date_evolution.setFormatter(logging.Formatter("%(message)s"))
        bloom_date_evolution.setLevel(logging.INFO)
        bloom_date_log.addHandler(bloom_date_evolution)
        bloom_date_log.propagate = False

    def _get_forcing_data(self):
        """Collect and process forcing data."""
        if not self.config.get_forcing_data:
            log.info("Skipped collection and processing of forcing data")
            return
        wind = WindProcessor(self.config)
        self.config.data_date = wind.make_forcing_data_file()
        log.info(
            "based on wind data forcing data date is {}".format(
                self.config.data_date.format("YYYY-MM-DD")
            )
        )
        try:
            with open("wind_data_date", "rt") as f:
                last_data_date = arrow.get(f.readline().strip()).date()
        except IOError:
            # Fake a wind data date to get things rolling
            last_data_date = self.config.run_start_date.date()
        if self.config.data_date == last_data_date:
            raise NoNewWindData
        else:
            with open("wind_data_date", "wt") as f:
                f.write("{}\n".format(self.config.data_date.format("YYYY-MM-DD")))
        meteo = MeteoProcessor(self.config)
        meteo.make_forcing_data_files()
        rivers = RiversProcessor(self.config)
        rivers.make_forcing_data_files()

    def _run_SOG(self):
        """Run SOG."""
        if not self.config.run_SOG:
            log.info("Skipped running SOG")
            return
        processes = {}
        base_infile = self.config.infiles["base"]
        for key in self.config.infiles["edits"]:
            proc = SOGcommand.api.run(
                self.config.SOG_executable,
                base_infile,
                self.config.infiles["edits"][key],
                key + ".stdout",
            )
            processes[key] = proc
            log.info(
                "SOG {0} run started at {1:%Y-%m-%d %H:%M:%S} as pid {2}".format(
                    key, datetime.datetime.now(), proc.pid
                )
            )
        while processes:
            time.sleep(30)
            for key, proc in copy(processes).items():
                if proc.poll() is None:
                    continue
                else:
                    processes.pop(key)
                    log.info(
                        "SOG {0} run finished at {1:%Y-%m-%d %H:%M:%S}".format(
                            key, datetime.datetime.now()
                        )
                    )

    def _get_results_timeseries(self):
        """Read SOG results time series of interest and create
        SOG_Timeseries objects from them.
        """
        self.nitrate, self.diatoms = {}, {}
        self.temperature, self.salinity = {}, {}
        self.mixing_layer_depth = {}
        for key in self.config.infiles["edits"]:
            std_bio_ts_outfile = self.config.std_bio_ts_outfiles[key]
            std_phys_ts_outfile = self.config.std_phys_ts_outfiles[key]
            self.nitrate[key] = SOG_Timeseries(std_bio_ts_outfile)
            self.nitrate[key].read_data("time", "3 m avg nitrate concentration")
            self.nitrate[key].calc_mpl_dates(self.config.run_start_date)
            self.diatoms[key] = SOG_Timeseries(std_bio_ts_outfile)
            self.diatoms[key].read_data("time", "3 m avg micro phytoplankton biomass")
            self.diatoms[key].calc_mpl_dates(self.config.run_start_date)
            self.temperature[key] = SOG_Timeseries(std_phys_ts_outfile)
            self.temperature[key].read_data("time", "3 m avg temperature")
            self.temperature[key].calc_mpl_dates(self.config.run_start_date)
            self.salinity[key] = SOG_Timeseries(std_phys_ts_outfile)
            self.salinity[key].read_data("time", "3 m avg salinity")
            self.salinity[key].calc_mpl_dates(self.config.run_start_date)
            self.mixing_layer_depth[key] = SOG_Timeseries(std_phys_ts_outfile)
            self.mixing_layer_depth[key].read_data("time", "mixing layer depth")
            self.mixing_layer_depth[key].calc_mpl_dates(self.config.run_start_date)

    def _create_timeseries_graphs(self):
        """Create time series graph objects."""
        self.fig_nitrate_diatoms_ts = self._two_axis_timeseries(
            self.nitrate,
            self.diatoms,
            titles=(
                "3 m Avg Nitrate Concentration [uM N]",
                "3 m Avg Diatom Biomass [uM N]",
            ),
            colors=(self.nitrate_colours, self.diatoms_colours),
        )
        self.fig_temperature_salinity_ts = self._two_axis_timeseries(
            self.temperature,
            self.salinity,
            titles=("3 m Avg Temperature [deg C]", "3 m Avg Salinity [-]"),
            colors=(self.temperature_colours, self.salinity_colours),
        )
        self.fig_mixing_layer_depth_ts = self._mixing_layer_depth_timeseries()

    def _two_axis_timeseries(self, left_ts, right_ts, titles, colors):
        """Create a time series graph figure object with 2 time series
        plotted on the left and right y axes.
        """
        fig = Figure((8, 3), facecolor="white")
        ax_left = fig.add_subplot(1, 1, 1)
        ax_left.set_position((0.125, 0.1, 0.775, 0.75))
        fig.ax_left = ax_left
        ax_right = ax_left.twinx()
        ax_right.set_position(ax_left.get_position())
        predicate = left_ts["avg_forcing"].mpl_dates >= date2num(self.config.data_date)
        for key in "early_bloom_forcing late_bloom_forcing".split():
            ax_left.plot(
                left_ts[key].mpl_dates[predicate],
                left_ts[key].dep_data[predicate],
                color=colors[0]["bounds"],
            )
            ax_right.plot(
                right_ts[key].mpl_dates[predicate],
                right_ts[key].dep_data[predicate],
                color=colors[1]["bounds"],
            )
        ax_left.plot(
            left_ts["avg_forcing"].mpl_dates,
            left_ts["avg_forcing"].dep_data,
            color=colors[0]["avg"],
        )
        ax_right.plot(
            right_ts["avg_forcing"].mpl_dates,
            right_ts["avg_forcing"].dep_data,
            color=colors[1]["avg"],
        )
        ax_left.set_ylabel(titles[0], color=colors[0]["avg"], size="x-small")
        ax_right.set_ylabel(titles[1], color=colors[1]["avg"], size="x-small")
        # Add line to mark switch from actual to averaged forcing data
        fig.data_date_line = ax_left.axvline(
            date2num(self.config.data_date), color="black"
        )
        # Format x-axis
        ax_left.xaxis.set_major_locator(MonthLocator())
        ax_left.xaxis.set_major_formatter(DateFormatter("%j\n%b"))
        for axis in (ax_left, ax_right):
            for label in axis.get_xticklabels() + axis.get_yticklabels():
                label.set_size("x-small")
        ax_left.set_xlim(
            (
                int(left_ts["avg_forcing"].mpl_dates[0]),
                math.ceil(left_ts["avg_forcing"].mpl_dates[-1]),
            )
        )
        ax_left.set_xlabel(
            "Year-days in {0} and {1}".format(
                self.config.run_start_date.year, self.config.run_start_date.year + 1
            ),
            size="x-small",
        )
        return fig

    def _mixing_layer_depth_timeseries(self):
        """Create a time series graph figure object of the mixing
        layer depth on the wind data date and the 6 days preceding it.
        """
        fig = Figure((8, 3), facecolor="white")
        ax = fig.add_subplot(1, 1, 1)
        ax.set_position((0.125, 0.1, 0.775, 0.75))
        predicate = np.logical_and(
            self.mixing_layer_depth["avg_forcing"].mpl_dates
            > date2num(self.config.data_date - datetime.timedelta(days=6)),
            self.mixing_layer_depth["avg_forcing"].mpl_dates
            <= date2num(self.config.data_date + datetime.timedelta(days=1)),
        )
        mpl_dates = self.mixing_layer_depth["avg_forcing"].mpl_dates[predicate]
        dep_data = self.mixing_layer_depth["avg_forcing"].dep_data[predicate]
        ax.plot(mpl_dates, dep_data, color="magenta")
        ax.set_ylabel("Mixing Layer Depth [m]", color="magenta", size="x-small")
        # Add line to mark profile time
        profile_datetime = datetime.datetime.combine(
            self.config.data_date, datetime.time(12)
        )
        profile_datetime_line = ax.axvline(date2num(profile_datetime), color="black")
        ax.xaxis.set_major_locator(DayLocator())
        ax.xaxis.set_major_formatter(DateFormatter("%j\n%d-%b"))
        ax.xaxis.set_minor_locator(HourLocator(interval=6))
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_size("x-small")
        ax.set_xlim((int(mpl_dates[0]), math.ceil(mpl_dates[-1])))
        ax.set_xlabel("Year-Day", size="x-small")
        fig.legend(
            [profile_datetime_line],
            ["Profile Time"],
            loc="upper right",
            prop={"size": "xx-small"},
        )
        return fig

    def _get_results_profiles(self):
        """Read SOG results profiles of interest and create
        SOG_HoffmuellerProfile objects from them.
        """
        self.nitrate_profile, self.diatoms_profile = {}, {}
        self.temperature_profile, self.salinity_profile = {}, {}
        for key in self.config.infiles["edits"]:
            Hoffmueller_outfile = self.config.Hoffmueller_profiles_outfiles[key]
            profile_number = (
                self.config.data_date - self.config.run_start_date.date()
            ).days
            self.nitrate_profile[key] = SOG_HoffmuellerProfile(Hoffmueller_outfile)
            self.nitrate_profile[key].read_data("depth", "nitrate", profile_number)
            self.diatoms_profile[key] = SOG_HoffmuellerProfile(Hoffmueller_outfile)
            self.diatoms_profile[key].read_data(
                "depth", "micro phytoplankton", profile_number
            )
            self.temperature_profile[key] = SOG_HoffmuellerProfile(Hoffmueller_outfile)
            self.temperature_profile[key].read_data(
                "depth", "temperature", profile_number
            )
            self.salinity_profile[key] = SOG_HoffmuellerProfile(Hoffmueller_outfile)
            self.salinity_profile[key].read_data("depth", "salinity", profile_number)

    def _create_profile_graphs(self):
        """Create profile graph objects."""
        profile_datetime = datetime.datetime.combine(
            self.config.data_date, datetime.time(12)
        )
        profile_dt = profile_datetime - self.config.run_start_date
        profile_hour = profile_dt.days * 24 + profile_dt.seconds / 3600
        self.mixing_layer_depth["avg_forcing"].boolean_slice(
            self.mixing_layer_depth["avg_forcing"].indep_data >= profile_hour
        )
        mixing_layer_depth = self.mixing_layer_depth["avg_forcing"].dep_data[0]
        self.fig_temperature_salinity_profile = self._two_axis_profile(
            self.temperature_profile["avg_forcing"],
            self.salinity_profile["avg_forcing"],
            mixing_layer_depth,
            titles=("Temperature [deg C]", "Salinity [-]"),
            colors=(self.temperature_colours, self.salinity_colours),
            limits=((4, 10), (20, 30)),
        )
        self.fig_nitrate_diatoms_profile = self._two_axis_profile(
            self.nitrate_profile["avg_forcing"],
            self.diatoms_profile["avg_forcing"],
            mixing_layer_depth,
            titles=("Nitrate Concentration [uM N]", "Diatom Biomass [uM N]"),
            colors=(self.nitrate_colours, self.diatoms_colours),
        )

    def _two_axis_profile(
        self,
        top_profile,
        bottom_profile,
        mixing_layer_depth,
        titles,
        colors,
        limits=None,
    ):
        """Create a profile graph figure object with 2 profiles
        plotted on the top and bottom x axes.
        """
        fig = Figure((4, 8), facecolor="white")
        ax_bottom = fig.add_subplot(1, 1, 1)
        ax_bottom.set_position((0.19, 0.1, 0.5, 0.8))
        ax_top = ax_bottom.twiny()
        ax_top.set_position(ax_bottom.get_position())
        ax_top.plot(
            top_profile.dep_data, top_profile.indep_data, color=colors[0]["avg"]
        )
        ax_top.set_xlabel(titles[0], color=colors[0]["avg"], size="small")
        ax_bottom.plot(
            bottom_profile.dep_data, bottom_profile.indep_data, color=colors[1]["avg"]
        )
        ax_bottom.set_xlabel(titles[1], color=colors[1]["avg"], size="small")
        for axis in (ax_bottom, ax_top):
            for label in axis.get_xticklabels() + axis.get_yticklabels():
                label.set_size("x-small")
        if limits is not None:
            ax_top.set_xlim(limits[0])
            ax_bottom.set_xlim(limits[1])
        ax_bottom.axhline(mixing_layer_depth, color="black")
        ax_bottom.text(
            x=ax_bottom.get_xlim()[1],
            y=mixing_layer_depth,
            s=" Mixing Layer\n Depth = {0:.2f} m".format(mixing_layer_depth),
            verticalalignment="center",
            size="small",
        )
        ax_bottom.set_ylim(
            (bottom_profile.indep_data[-1], bottom_profile.indep_data[0])
        )
        ax_bottom.set_ylabel("Depth [m]", size="small")
        return fig

    def _calc_bloom_date(self):
        """Calculate the predicted spring bloom date."""
        key = "avg_forcing"
        self.bloom_date, self.bloom_biomass = {}, {}
        for key in self.config.infiles["edits"]:
            self._clip_results_to_jan1(key)
            self._reduce_results_to_daily(key)
            first_low_nitrate_days = self._find_low_nitrate_days(
                key, NITRATE_HALF_SATURATION_CONCENTRATION
            )
            self._find_phytoplankton_peak(
                key, first_low_nitrate_days, PHYTOPLANKTON_PEAK_WINDOW_HALF_WIDTH
            )
        if self.config.get_forcing_data or self.config.run_SOG:
            line = "  {0}      {1}  {2:.4f}".format(
                self.config.data_date.format("YYYY-MM-DD"),
                self.bloom_date["avg_forcing"],
                self.bloom_biomass["avg_forcing"],
            )
            for key in "early_bloom_forcing late_bloom_forcing".split():
                line += "         {0}  {1:.4f}".format(
                    self.bloom_date[key], self.bloom_biomass[key]
                )
            bloom_date_log.info(line)

    def _clip_results_to_jan1(self, key):
        """Clip the nitrate concentration and diatom biomass results
        so that they start on 1-Jan of the bloom year.
        """
        jan1 = datetime.datetime(self.config.run_start_date.year + 1, 1, 1)
        discard_hours = jan1 - self.config.run_start_date
        discard_hours = discard_hours.days * 24 + discard_hours.seconds / 3600
        predicate = self.nitrate[key].indep_data >= discard_hours
        self.nitrate[key].boolean_slice(predicate)
        self.diatoms[key].boolean_slice(predicate)

    def _reduce_results_to_daily(self, key):
        """Reduce the nitrate concentration and diatom biomass results
        to daily values.

        Nitrate concentrations are daily minimum values.

        Diatom biomasses are daily maximum values.

        Independent data values are dates.
        """
        # Assume that there are an integral nummber of SOG time steps in a
        # day
        day_slice = 86400 // self.config.SOG_timestep
        day_iterator = range(
            0, self.nitrate[key].dep_data.shape[0] - day_slice, day_slice
        )
        jan1 = datetime.date(self.config.run_start_date.year + 1, 1, 1)
        self.nitrate[key].dep_data = np.array(
            [self.nitrate[key].dep_data[i : i + day_slice].min() for i in day_iterator]
        )
        self.nitrate[key].indep_data = np.array(
            [
                jan1 + datetime.timedelta(days=i)
                for i in range(self.nitrate[key].dep_data.size)
            ]
        )
        day_iterator = range(
            0, self.diatoms[key].dep_data.shape[0] - day_slice, day_slice
        )
        self.diatoms[key].dep_data = np.array(
            [self.diatoms[key].dep_data[i : i + day_slice].max() for i in day_iterator]
        )
        self.diatoms[key].indep_data = np.array(
            [
                jan1 + datetime.timedelta(days=i)
                for i in range(self.diatoms[key].dep_data.size)
            ]
        )

    def _find_low_nitrate_days(self, key, threshold):
        """Return the start and end dates of the first 2 day period in
        which the nitrate concentration is below the ``threshold``.
        """
        key_string = key.replace("_", " ")
        self.nitrate[key].boolean_slice(self.nitrate[key].dep_data <= threshold)
        log.debug(
            "Dates on which nitrate was <= {0} uM N with {1}:\n{2}".format(
                threshold, key_string, self.nitrate[key].indep_data
            )
        )
        log.debug(
            "Nitrate <= {0} uM N with {1}:\n{2}".format(
                threshold, key_string, self.nitrate[key].dep_data
            )
        )
        for i in range(self.nitrate[key].dep_data.shape[0]):
            low_nitrate_day_1 = self.nitrate[key].indep_data[i]
            days = self.nitrate[key].indep_data[i + 1] - low_nitrate_day_1
            if days == datetime.timedelta(days=1):
                low_nitrate_day_2 = self.nitrate[key].indep_data[i + 1]
                break
        return low_nitrate_day_1, low_nitrate_day_2

    def _find_phytoplankton_peak(self, key, first_low_nitrate_days, peak_half_width):
        """Return the date with ``peak_half_width`` of the
        ``first_low_nitrate_days`` on which the diatoms biomass is the
        greatest.
        """
        key_string = key.replace("_", " ")
        half_width_days = datetime.timedelta(days=peak_half_width)
        early_bloom_date = first_low_nitrate_days[0] - half_width_days
        late_bloom_date = first_low_nitrate_days[1] + half_width_days
        log.debug(
            "Bloom window for {0} is between {1} and {2}".format(
                key_string, early_bloom_date, late_bloom_date
            )
        )
        self.diatoms[key].boolean_slice(
            self.diatoms[key].indep_data >= early_bloom_date
        )
        self.diatoms[key].boolean_slice(self.diatoms[key].indep_data <= late_bloom_date)
        log.debug(
            "Dates in {0} bloom window:\n{1}".format(
                key_string, self.diatoms[key].indep_data
            )
        )
        log.debug(
            "Micro phytoplankton biomass values in "
            "{0} bloom window:\n{1}".format(key_string, self.diatoms[key].dep_data)
        )
        bloom_date_index = self.diatoms[key].dep_data.argmax()
        self.bloom_date[key] = self.diatoms[key].indep_data[bloom_date_index]
        self.bloom_biomass[key] = self.diatoms[key].dep_data[bloom_date_index]
        log.info(
            "Predicted {0} bloom date is {1}".format(key_string, self.bloom_date[key])
        )
        log.debug(
            "Phytoplankton biomass on {0} bloom date is {1} uM N".format(
                key_string, self.bloom_biomass[key]
            )
        )


def clip_results_to_jan1(nitrate, diatoms, run_start_date):
    """Clip the nitrate concentration and diatom biomass results
    so that they start on 1-Jan of the bloom year.

    :arg nitrate: Nitrate concentration timeseries
    :type nitrate: dict of :py:class:`bloomcast.utils.SOG_Timeseries`
                   instances keyed by ensemble member identifier

    :arg diatoms: Diatom biomass timeseries
    :type diatoms: dict of :py:class:`bloomcast.utils.SOG_Timeseries`
                   instances keyed by ensemble member identifier

    :arg run_start_date: SOG run start date
    :type run_start_date: :py:class:`datetime.date`
    """
    jan1 = datetime.datetime(run_start_date.year + 1, 1, 1)
    discard_hours = jan1 - run_start_date
    discard_hours = discard_hours.days * 24 + discard_hours.seconds / 3600
    for member in nitrate:
        predicate = nitrate[member].indep_data >= discard_hours
        nitrate[member].boolean_slice(predicate)
        diatoms[member].boolean_slice(predicate)


def reduce_results_to_daily(nitrate, diatoms, run_start_date, SOG_timestep):
    """Reduce the nitrate concentration and diatom biomass results
    to daily values.

    Nitrate concentrations are daily minimum values.

    Diatom biomasses are daily maximum values.

    Independent data values are dates.

    :arg nitrate: Nitrate concentration timeseries
    :type nitrate: dict of :py:class:`bloomcast.utils.SOG_Timeseries`
                   instances keyed by ensemble member identifier

    :arg diatoms: Diatom biomass timeseries
    :type diatoms: dict of :py:class:`bloomcast.utils.SOG_Timeseries`
                   instances keyed by ensemble member identifier

    :arg run_start_date: SOG run start date
    :type run_start_date: :py:class:`datetime.date`

    :arg SOG_timestep: SOG run time-step
    :type SOG_timestep: int
    """
    # Assume that there are an integral nummber of SOG time steps in a
    # day
    day_slice = 86400 // SOG_timestep
    jan1 = datetime.date(run_start_date.year + 1, 1, 1)
    for member in nitrate:
        last_day = nitrate[member].dep_data.shape[0] - day_slice
        day_iterator = range(0, last_day, day_slice)
        nitrate[member].dep_data = np.array(
            [nitrate[member].dep_data[i : i + day_slice].min() for i in day_iterator]
        )
        nitrate[member].indep_data = np.array(
            [
                jan1 + datetime.timedelta(days=i)
                for i in range(nitrate[member].dep_data.size)
            ]
        )

        last_day = diatoms[member].dep_data.shape[0] - day_slice
        day_iterator = range(0, last_day, day_slice)
        diatoms[member].dep_data = np.array(
            [diatoms[member].dep_data[i : i + day_slice].max() for i in day_iterator]
        )
        diatoms[member].indep_data = np.array(
            [
                jan1 + datetime.timedelta(days=i)
                for i in range(diatoms[member].dep_data.size)
            ]
        )


def find_low_nitrate_days(nitrate, threshold):
    """Return the start and end dates of the first 2 day period in
    which the nitrate concentration is below the ``threshold``.
    """
    first_low_nitrate_days = {}
    for member in nitrate:
        nitrate[member].boolean_slice(nitrate[member].dep_data <= threshold)
        for i in range(nitrate[member].dep_data.shape[0]):
            low_nitrate_day_1 = nitrate[member].indep_data[i]
            days = nitrate[member].indep_data[i + 1] - low_nitrate_day_1
            if days == datetime.timedelta(days=1):
                low_nitrate_day_2 = nitrate[member].indep_data[i + 1]
                break
        first_low_nitrate_days[member] = (low_nitrate_day_1, low_nitrate_day_2)
    return first_low_nitrate_days


def find_phytoplankton_peak(diatoms, first_low_nitrate_days, peak_half_width):
    """Return the date within ``peak_half_width`` of the
    ``first_low_nitrate_days`` on which the diatoms biomass is the
    greatest.
    """
    half_width_days = datetime.timedelta(days=peak_half_width)
    bloom_dates, bloom_biomasses = {}, {}
    for member in diatoms:
        bloom_window_start = first_low_nitrate_days[member][0] - half_width_days
        bloom_window_end = first_low_nitrate_days[member][1] + half_width_days
        diatoms[member].boolean_slice(diatoms[member].indep_data >= bloom_window_start)
        diatoms[member].boolean_slice(diatoms[member].indep_data <= bloom_window_end)
        bloom_date_index = diatoms[member].dep_data.argmax()
        bloom_dates[member] = diatoms[member].indep_data[bloom_date_index]
        bloom_biomasses[member] = diatoms[member].dep_data[bloom_date_index]
    return bloom_dates, bloom_biomasses


def main():
    try:
        config_file = sys.argv[1]
    except IndexError:
        print("Expected config file path/name")
        sys.exit(1)
    try:
        data_date = arrow.get(sys.argv[2])
    except ValueError:
        print("Expected %Y-%m-%d for data date, got: {0[2]}".format(sys.argv))
        sys.exit(1)
    except IndexError:
        data_date = None
    bloomcast = Bloomcast(config_file, data_date)
    bloomcast.run()
