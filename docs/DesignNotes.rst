.. DesignNotes-section:

Design Notes
============

A SoG Bloomcast run on a given day is composed of the following steps:

#. Collect the forcing data for the year in which the run is being
   initialized for the period from 1-Jan to the day before the current
   date from various web sites. The forcing data are:

   * Sandheads wind
   * YVR meteorology (air temperature, relative humidity, and cloud
     fraction)
   * Fraser River discharge at Hope
   * Englishman River discharge at Parksville

#. Process the forcing data into data files in the format expected by
   SOG, and deal with missing data. There are 3 missing data
   scenarios:

   #. Data for the day before the current date is unavailable:

      * For wind data this means that the run will not be done for the
        current data:

        * Send an email alert indicating that the run was aborted due to
          lack of wind data.

        * Update the results web page with a message that there was no run
          for the current day and so the best estimate of the spring bloom
          date remains that from the last completed run.

      * For meteorological and river discharge data, use the preceding
        day's values

   #. Data for the day before the current date is available but data
      for an earlier day is missing:

      * For wind data, interpolate values for the missing days using
        the algorithm developed by Jeremy Sklad

      * For meteorological and river discharge data, interpolate
        values for the missing days using linear interpolation

   #. Wind data for 2 days before the current date was unavailable 1
      day ago but *is* available today, but data for the day before
      the current date is *unavailable* (i.e. wind data is lagging by
      1 day):

      * This means that there was no run done for the day before the
        current date, but now a run for that date could be done, so do
        so.

        * Send an email alert indicating that the estimated spring
          bloom date has been updated using the wind data from 2 days
          before the current date.

        * Update the results web page with a message that there was no run
          for the current day and so the best estimate of the spring bloom
          date remains that from the last completed run.
