**************************************************************
${data_date.format('YYYY-MM-DD')} Spring Diatom Bloom Forecast
**************************************************************

The current best estimate of the first spring diatom bloom in the Strait of Georgia is ${'{:%Y-%m-%d}'.format(bloom_dates[prediction['median']])}.
That estimate is based on a run of the `SOG biophysical model for deep estuaries`_ [#]_ with the following parameters:

* Run start date/time: ${'{:%Y-%m-%d}'.format(run_start_date)}
* Actual wind,
  meteorological,
  and river flow forcing data to ${data_date.format('YYYY-MM-DD')},
  and historical data from ${prediction['median']} thereafter

${prediction['median']} has the median bloom date in an ensemble of SOG runs that use historical wind,
meteorological,
and river flow data from 1980 through 2010 as future forcing data after ${data_date.format('YYYY-MM-DD')}.

Best estimate bounds on the bloom date are:

* No earlier than ${'{:%Y-%m-%d}'.format(bloom_dates[prediction['early']])} based on using actual forcing data to ${data_date.format('YYYY-MM-DD')},
  and data from ${prediction['early'] - 1}/${prediction['early']} thereafter.
  ${prediction['early']} has the 5th centile bloom date in the ensemble of SOG runs.

* No later than ${'{:%Y-%m-%d}'.format(bloom_dates[prediction['late']])} based on using actual forcing data to ${data_date.format('YYYY-MM-DD')},
  and data from ${prediction['late'] - 1}/${prediction['late']} thereafter.
  ${prediction['late']} has the 95th centile bloom date in the ensemble of SOG runs.

.. [#] Allen, S. E. and M. A. Wolfe, Hindcast of the Timing of the Spring Phytoplankton Bloom in the Strait of Georgia, 1968-2010. Progress in Oceanography, vol 115, pp 6-13 (2013). http://dx.doi.org/10.1016/j.pocean.2013.05.026

.. _SOG biophysical model for deep estuaries: http://www.eos.ubc.ca/~sallen/SOG-docs/


Data Sources
============

The forcing data used to drive the SOG model is obtained from several sources:

* Hourly wind velocities at `Sand Heads Lightstation` from the bulk data web service at `climate.weatheroffice.gc.ca/climateData/`_

* Hourly air temperature,
  relative humidity,
  and weather description
  (from which cloud fraction is calculated)
  at Vancouver International Airport
  (YVR)
  from the bulk data web service at `climate.weatheroffice.gc.ca/climateData/`_

* Average daily river discharge rates for the `Fraser River`_,
  and the `Englishman River`_
  (as a proxy for the fresh water sources other than the Fraser)
  from `wateroffice.ec.gc.ca`_

.. _Sand Heads Lightstation: http://www.lighthousefriends.com/light.asp?ID=1178
.. _climate.weatheroffice.gc.ca/climateData/: http://climate.weatheroffice.gc.ca/climateData/
.. _Fraser River: http://www.aquatic.uoguelph.ca/rivers/fraser.htm
.. _Englishman River: http://en.wikipedia.org/wiki/Englishman_River
.. _wateroffice.ec.gc.ca: http://wateroffice.ec.gc.ca/


Disclaimer
==========

This site presents output from a research project.
Results are not expected to be a robust prediction of the timing of the spring bloom.
At this point,
we believe such a prediction is not possible before mid-February using any model and this model is not yet tested.


Time Series
===========

.. image:: ${plots_path}/${ts_plot_files['nitrate_diatoms']}
   :class: img-responsive

.. image:: ${plots_path}/${ts_plot_files['temperature_salinity']}
   :class: img-responsive

.. image:: ${plots_path}/${ts_plot_files['mld_wind']}
   :class: img-responsive


Profiles at ${data_date.format('YYYY-MM-DD')} 12:00 from Median Prediction
==========================================================================

.. image:: ${plots_path}/${profiles_plot_file}
   :class: img-responsive


Bloom Date Evolution
====================

.. raw:: html

    <table class="table-striped">
      <thead>
        <tr>
          <th class="transition-date" rowspan="2">
            Actual to Ensemble Forcing Transition Date</th>
          <th class="centre-span2" colspan="2">Median</th>
          <th class="centre-span2" colspan="2">5th Centile Early Bound</th>
          <th class="centre-span2" colspan="2">95th Centile Late Bound</th>
          <th class="centre-span2" colspan="2">Earliest Ensemble Result</th>
          <th class="centre-span2" colspan="2">Latest Ensemble Result</th>
        </tr>
        <tr>
          %for i in range(5):
            <th class="bloom-date">Bloom Date</th>
            <th class="ensemble-member">Ensemble Member</th>
          %endfor
        </tr>
      </thead>
      <tbody>
        %for row in bloom_date_log:
          <tr>
            %for value in row:
              <td>${value}</td>
            %endfor
            %for i in range(len(row) + 1, 12):
              <td>N/A</td>
            %endfor
          </tr>
        %endfor
      </tbody>
  </table>
