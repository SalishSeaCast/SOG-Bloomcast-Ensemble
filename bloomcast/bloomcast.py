"""Driver module for SoG-bloomcast project
"""
from __future__ import absolute_import
from __future__ import division
# Standard library:
from datetime import date
from datetime import datetime
from datetime import timedelta
import logging
import logging.handlers
from subprocess import Popen
from subprocess import STDOUT
import sys
# NumPy:
import numpy as np
# Bloomcast:
from meteo import MeteoProcessor
from rivers import RiversProcessor
from utils import Config
from utils import SOG_Timeseries
from wind import WindProcessor


log = logging.getLogger('bloomcast')


def run(config_file):
    """Run the bloomcast process.

    * Load the process configuration data.

    * Get the wind forcing data.

    * Get the meteorological and river flow forcing data.

    * Run the SOG code.
    """
    config = Config()
    config.load_config(config_file)
    configure_logging(config)
    log.debug('run start date is {0:%Y-%m-%d}'.format(config.run_start_date))
    get_forcing_data(config)
    run_SOG(config)
    calc_bloom_date(config)


def get_forcing_data(config):
    """Collect and process forcing data.
    """
    if  not config.get_forcing_data:
        log.info('Skipped collection and processing of forcing data')
        return
    wind = WindProcessor(config)
    config.data_date = wind.make_forcing_data_file()
    log.info('based on wind data run data date is {0:%Y-%m-%d}'
              .format(config.data_date))
    meteo = MeteoProcessor(config)
    meteo.make_forcing_data_files()
    rivers = RiversProcessor(config)
    rivers.make_forcing_data_files()


def run_SOG(config):
    """Run SOG.
    """
    if not config.run_SOG:
        log.info('Skipped running SOG')
        return
    log.info('SOG run started at {0:%Y-%m-%d %H:%M:%S}'.format(datetime.now()))
    with open(config.infile, 'rt') as infile_obj:
        with open(config.infile + '.stdout', 'wt') as stdout_obj:
            SOG = Popen('nice -19 ../SOG-code-ocean/SOG'.split(),
                        stdin=infile_obj, stdout=stdout_obj, stderr=STDOUT)
            SOG.wait()
    log.info(
        'SOG run finished at {0:%Y-%m-%d %H:%M:%S}'.format(datetime.now()))


def calc_bloom_date(config):
    """Calculate the predicted spring bloom date.

    From Allen & Wolfe, in preparation:

    "Although the idea of a spring bloom is well-defined, the exact
    timing of a real spring bloom is not.  In C09 the peak of the
    bloom was defined as the highest concentration of phytoplankton
    unless an earlier bloom (more than 5 days earlier) was associated
    with nitrate going to zero.  J.Gower using satellite data chooses
    a measure of the start of the bloom as the time when the whole
    Strait of Georgia has high chlorophyll.  The nutritional quality
    of the phytoplankton appears to change when they become nutrient
    limited \citep{SastriDower2009}.  Thus here we use a definition
    that should delineate between nutrient replete spring conditions
    and nutrient stressed summer conditions.  We use the peak
    phytoplankton concentration (averaged from the surface to 3 m
    depth) within four days of the average 0-3~m nitrate concentration
    going below 0.5 uM (the half-saturation concentration) for two
    consecutive days."
    """
    NITRATE_HALF_SATURATION_CONCENTRATION = 0.5  # uM
    PHYTOPLANKTON_PEAK_WINDOW_HALF_WIDTH = 4     # days
    nitrate = SOG_Timeseries(config.std_bio_ts_outfile)
    nitrate.read_data('time', '3 m avg nitrate concentration')
    diatoms = SOG_Timeseries(config.std_bio_ts_outfile)
    diatoms.read_data('time', '3 m avg micro phytoplankton biomass')
    nitrate, diatoms = clip_results_to_Jan1(config, nitrate, diatoms)
    nitrate, diatoms = reduce_results_to_daily(
        config, nitrate, diatoms)
    first_low_nitrate_days = find_low_nitrate_days(
        nitrate, NITRATE_HALF_SATURATION_CONCENTRATION)
    bloom_date = find_phytoplankton_peak(
        diatoms, first_low_nitrate_days, PHYTOPLANKTON_PEAK_WINDOW_HALF_WIDTH)


def clip_results_to_Jan1(config, nitrate, diatoms):
    """Clip the nitrate and micro phytoplankton biomass results so
    that they start on 1-Jan of the bloom year.
    """
    jan1 = datetime(config.run_start_date.year + 1, 1, 1)
    discard_hours = (jan1 - config.run_start_date)
    discard_hours = discard_hours.days * 24 + discard_hours.seconds / 3600
    predicate = nitrate.indep_data >= discard_hours
    nitrate.boolean_slice(predicate)
    diatoms.boolean_slice(predicate)
    return nitrate, diatoms


def reduce_results_to_daily(config, nitrate, diatoms):
    """Reduce the nitrate concentration and micro phytoplankton
    biomass results to daily values.

    Nitrate concentrations are daily minimum values.

    Micro phytoplankton biomasses are daily maximum values.

    Independent data values are dates.
    """
    # Assume that there are an integral nummber of SOG time steps in a
    # day
    day_slice = 86400 // config.SOG_timestep
    year = config.run_start_date.year + 1
    nitrate.dep_data = np.array(
        [nitrate.dep_data[i:i+day_slice].min()
         for i in xrange(0, nitrate.dep_data.shape[0] - day_slice, day_slice)])
    nitrate.indep_data = np.array(
        [date.fromordinal(i+1).replace(year=year)
         for i in xrange(nitrate.dep_data.shape[0])])
    diatoms.dep_data = np.array(
        [diatoms.dep_data[i:i+day_slice].max()
         for i in xrange(0, diatoms.dep_data.shape[0] - day_slice, day_slice)])
    diatoms.indep_data = np.array(
        [date.fromordinal(i+1).replace(year=year)
         for i in xrange(diatoms.dep_data.shape[0])])
    return nitrate, diatoms


def find_low_nitrate_days(nitrate, threshold):
    """Return the start and end dates of the first 2 day period in
    which the ``nitrate`` concentration is below the ``threshold``.
    """
    nitrate.boolean_slice(nitrate.dep_data <= threshold)
    log.debug('Dates on which nitrate was <= {0} uM N:\n{1}'
              .format(threshold, nitrate.indep_data))
    log.debug('Nitrate <= {0} uM N:\n{1}'
              .format(threshold, nitrate.dep_data))
    for i in xrange(nitrate.dep_data.shape[0]):
        low_nitrate_day_1 = nitrate.indep_data[i]
        if nitrate.indep_data[i+1] - low_nitrate_day_1 == timedelta(days=1):
            low_nitrate_day_2 = nitrate.indep_data[i+1]
            break
    return low_nitrate_day_1, low_nitrate_day_2


def find_phytoplankton_peak(diatoms, first_low_nitrate_days, peak_half_width):
    """Return the date with ``peak_half_width`` of the
    ``first_low_nitrate_days`` on which the ``diatoms`` biomass is the
    greatest.
    """
    half_width_days = timedelta(days=peak_half_width)
    early_bloom_date = first_low_nitrate_days[0] - half_width_days
    late_bloom_date = first_low_nitrate_days[1] + half_width_days
    log.debug('Bloom window is between {0} and {1}'
              .format(early_bloom_date, late_bloom_date))
    diatoms.boolean_slice(diatoms.indep_data >= early_bloom_date)
    diatoms.boolean_slice(diatoms.indep_data <= late_bloom_date)
    log.debug('Dates in bloom window:\n{0}'.format(diatoms.indep_data))
    log.debug('Micro phytoplankton biomass values in bloom window:\n{0}'
              .format(diatoms.dep_data))
    bloom_date_index = diatoms.dep_data.argmax()
    bloom_date = diatoms.indep_data[bloom_date_index]
    log.info('Predicted bloom date is {0}'.format(bloom_date))
    log.debug(
        'Phytoplankton biomass on bloom date is {0} uM N'
        .format(diatoms.dep_data[bloom_date_index]))
    return bloom_date


def configure_logging(config):
    """Configure logging of debug & warning messages to console and email.

    Debug logging on/off & email recipient(s) for warning messages are
    set in config file.
    """
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    if config.logging.debug:
        console.setLevel(logging.DEBUG)
    log.addHandler(console)
    mailhost = (('localhost', 1025) if config.logging.use_test_smtpd
                else 'localhost')
    email = logging.handlers.SMTPHandler(
        mailhost, fromaddr='SoG-bloomcast@eos.ubc.ca',
        toaddrs=config.logging.toaddrs,
        subject='Warning Message from SoG-bloomcast')
    email.setFormatter(formatter)
    email.setLevel(logging.WARNING)
    log.addHandler(email)


if __name__ == '__main__':
    run(sys.argv[1])
