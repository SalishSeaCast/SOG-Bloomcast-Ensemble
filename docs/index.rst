.. SoG Bloomcast documentation master file

SoG Bloomcast Documentation
===========================

The SoG Bloomcast project is a framework to automatically do a daily
run of the SOG biophysical model for the southern Strait of Georgia to
provide a current best estimate of the date of the spring
phytoplankton boom.

SoG Bloomcast collects forcing data (wind velocity, meteorological
data, and river flows) from "live" web sources that are updated
daily. The data from those sources is used for dates between the
initialization date of the run and the current date, and averaged data
is used for dates after the run date.

The results are reported via daily updates of a public web page that
provides:

* The latest best estimate of the spring phytoplankton bloom date,
  along with an estimate of the accuracy of the prediction

* Timeseries graphs of:

  * Nitrate concentration averaged over the top 3 m of the water
    column
  * Diatom phytoplankton biomass averaged over the top 3 m of the
    water column
  * Water temperature and salinity averaged over the top 3 m of the
    water column

  for the duration of the run

* Profile graphs of:

  * Nitrate concentration
  * Diatom phytoplankton biomass

  for noon local standard time (LST) on the run date

Run to run results that show the evolution of the bloom date
predictions are also retained for analysis, but are not presented on
the public results page.


Contents:

.. toctree::
   :maxdepth: 2

   DesignNotes

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

