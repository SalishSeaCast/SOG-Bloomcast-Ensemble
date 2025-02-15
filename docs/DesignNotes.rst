.. _DesignNotes-section:

Design Notes
============

A SoG Bloomcast run on a given day is composed of the following steps:

#. Collect the forcing data for the year in which the run is being
   initialized for the period from 1-Jan to the day before the current
   date from various web sites. The forcing data are:

   * Sandheads wind from
     http://www.climate.weatheroffice.gc.ca/climateData/bulkdata_e.html?timeframe=1&Prov=BC&StationID=6831&Year=2011&Month=8&Day=27&format=xml
     with date values set appropriately; response is a XML data file
     sent as a download
   * YVR meteorology (air temperature, relative humidity, and cloud
     fraction)
     http://www.climate.weatheroffice.gc.ca/climateData/bulkdata_e.html?timeframe=1&Prov=BC&StationID=889&Year=2011&Month=8&Day=28%format=xml
     with date values set appropriately; response is a XML data file
     sent as a download
   * Fraser River discharge at Hope from
     http://www.wateroffice.ec.gc.ca/graph/graph_e.html?mode=text&stn=08MF005&prm1=6&syr=2011&smo=8&sday=22&eyr=2011&emo=8&eday=30
     with date values set appropriately

     * session cookie indicating acceptance of data quality disclaimer
       must be set
     * reponse is an HTML page containing a well-formed table of
       date/time and discharge values at 15 minute intervals

   * Englishman River discharge at Parksville
     http://www.wateroffice.ec.gc.ca/graph/graph_e.html?mode=text&stn=08HB002&prm1=3&syr=2011&smo=08&sday=01&eyr=2011&emo=08&eday=30
     with date values set appropriately

     * session cookie indicating acceptance of data quality disclaimer
       must be set
     * reponse is an HTML page containing a well-formed table of
       date/time and discharge values at 5 minute intervals


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

#. Run SOG with an :file:`infile` that is tuned for the spring diatom
   bloom and provides appropriate bloomcast parameter values:

   * :kbd:`init datetime`
       typically :kbd:`yyyy-09-19 18:49:00`, where :kbd:`yyyy` is the
       year before the one for which the bloom is being forecast; or
       :kbd:`yyyy-09-18 18:49:00` when that year is a leap year

   * :kbd:`end datetime`
       typically :kbd:`yyyy-05-01 00:49:00`, where :kbd:`yyyy` is the
       year for which the bloom is being forecast

   * :kbd:`ctd_in` CTD profile initialization file
       typically :file:`SOG-initial/SG-39-2001-09-19.sog`

       .. note::

          The 2001-09-19 CTD cast is used for initialization for
          several reasons: CTD cast data for the current year is often
          not available until several months after the desired
          early-autumn start date for bloomcast runs, the 2001-09-19
          data is a good proxy for average conditions, and the
          influence of the initial conditions on the SOG model results
          disappears 10 to 20 days after the run start date.

   * :kbd:`nuts_in` nitrate and silicon profiles initialization file
       typically :file:`SOG-initial/Nuts-39-2001-09-19.sog`

   * Suitable file names for timeseries and profile results output
     files

   * :kbd:`profday` year-day for profile
       run date

   * The names of the forcing data files created in step 2 above.

   The version of SOG used for bloomcast includes Susan's 2011 changes
   to the :file:`forcing.f90` module that transitions from the forcing
   data in the infile to averaged forcing data when the former runs
   out.


#. Generate timeseries and profile graphs from SOG run results (see
   :ref:`SoG-BloomcastDocs-doc`).


#. Use Susan's spring bloom identification algorithm to calculate the
   estimated date of the spring diatom phytoplanktion bloom, and its
   uncertainty.


#. Generate the HTML code for the public web page summarizing the
   bloomcast results from the run by substituting the graphs and
   results calculated above into the page template.


#. Generate the HTML code for the private web page of run to run
   results.


#. Push the web pages to the http://stratogem.ubc.ca domain.


.. _ForcingDataProcessing-section:

Forcing Data Processing
-----------------------


.. _WindTranformation-section:

Wind Transformation
~~~~~~~~~~~~~~~~~~~

Environment Canada provides wind velocity data in the form of speed in
km/hr and direction in 10s of degrees. SOG expects wind velocites as
cross- and along-estuary components in m/s. For the Strait of Geogria
the along-estuary direction is 305\ |deg|. SOG also expects the vector
direction oriented so that it is consistent with ocean currents;
i.e. westerly currents and winds demote flow *to* the west.

.. |deg| unicode:: 0xb0

This snippet of Python shows the transformation algorithm in detail::

  # Convert speed from km/hr to m/s
  speed = speed * 1000 / (60 * 60)
  # Convert direction from 10s of degrees to degrees
  direction = direction * 10
  # Convert speed and direction to u and v components
  radian_direction = radians(direction)
  u_wind = speed * sin(radian_direction)
  v_wind = speed * cos(radian_direction)
  # Rotate components to align u direction with Strait
  strait_heading = radians(305)
  cross_wind = u_wind * cos(strait_heading) - v_wind * sin(strait_heading)
  along_wind = u_wind * sin(strait_heading) + v_wind * cos(strait_heading)
  # Resolve atmosphere/ocean direction difference in favour of
  # oceanography
  cross_wind = -cross_wind
  along_wind = -along_wind
