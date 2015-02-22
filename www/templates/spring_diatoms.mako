*****************************************
${data_date} Spring Diatom Bloom Forecast
*****************************************

Summary blurb

[1] Allen, S. E. and M. A. Wolfe, Hindcast of the Timing of the Spring Phytoplankton Bloom in the Strait of Georgia, 1968-2010. Progress in Oceanography, vol 115, pp 6-13 (2013). http://dx.doi.org/10.1016/j.pocean.2013.05.026


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

.. raw:: html

    <object class="img-responsive" type="image/svg+xml"
            data="${plots_path}/${ts_plot_files['nitrate_diatoms']}">
    </object>
    <object class="img-responsive" type="image/svg+xml"
            data="${plots_path}/${ts_plot_files['temperature_salinity']}">
    </object>
    <object class="img-responsive" type="image/svg+xml"
            data="${plots_path}/${ts_plot_files['mld_wind']}">
    </object>


Profiles at ${data_date} 12:00
==============================

.. raw:: html

    <object class="img-responsive" type="image/svg+xml"
            data="${plots_path}/${profiles_plot_file}">
    </object>


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
