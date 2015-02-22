.. _Deployment:

Deployment
==========

Environment
-----------

Set up a :ref:`DevelopmentAndDeploymentEnvironment` on :kbd:`salish`,
excluding the testing and debugging tools.


Input Files
-----------

Create a SOG input YAML file for the year's bloomcast runs in the :file:`run/` directory.
That is most easily done by copying and editing the previous year's file.
For 2015:

.. code-block:: bash

    (bloomcast)$ hg cp 2014_bloomcast_infile.yaml 2015_bloomcast_infile.yaml

and set the values of the following items to appropriate values:

* :kbd:`initial_conditions[init_datetime]`
* :kbd:`end_datetime`
* :kbd:`profile_results[hoffmueller_start_year]`
* :kbd:`profile_results[hoffmueller_end_year]`

.. code-block:: yaml

    ...

    initial_conditions:
      init_datetime:
        value: 2014-09-19 18:49:00
        variable_name: initDatetime
        description: initial CTD profile date/time

    ...

    end_datetime:
      value: 2015-05-01 00:49:00
      variable_name: endDatetime
      description: end of run date/time

    ...

    hoffmueller_start_year:
      value: 2014
      variable_name: Hoff_startyr
      description: year to start Hoffmueller results output

    ...

    hoffmueller_end_year:
      value: 2015
      variable_name: Hoff_endyr
      description: year to end Hoffmueller results output

Edit the :file:`run/config.yaml` file to point to the year's infile via the :kbd:`ensemble[base_infile]` item:

.. code-block:: yaml

    ...

    ensemble:
      ...
      base_infile: 2015_bloomcast_infile.yaml

    ...

