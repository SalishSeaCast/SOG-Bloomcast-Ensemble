.. _Deployment:

Deployment
==========

Environment
-----------

Set up a :ref:`DevelopmentAndDeploymentEnvironment` on :kbd:`salish`,
excluding the testing and debugging tools:

.. code-block:: bash

    pixi install -e default


Input Files
-----------

Create a SOG input YAML file for the year's bloomcast runs in the :file:`run/` directory.
That is most easily done by copying and editing the previous year's file.
Example:

.. code-block:: bash

    cp 2025_bloomcast_infile.yaml 2026_bloomcast_infile.yaml

and set the values of the following items to appropriate values:

* ``initial_conditions[init_datetime]``
* ``end_datetime``
* ``timeseries_results[*]``
* ``profiles_results[*_file]``
* ``profiles_results[hoffmueller_start_year]``
* ``profiles_results[hoffmueller_end_year]``

.. code-block:: yaml

    ...

    initial_conditions:
      init_datetime:
        value: 2025-09-19 18:49:00
        variable_name: initDatetime
        description: initial CTD profile date/time

    ...

    end_datetime:
      value: 2026-05-01 00:49:00
      variable_name: endDatetime
      description: end of run date/time

    ...

    timeseries_results:
      std_physics:
        value: timeseries/std_phys_2025_bloomcast.out
        variable_name: std_phys_ts_out
        description: path/filename for standard physics time series output
      user_physics:
        value: timeseries/user_phys_2025_bloomcast.out
        variable_name: user_phys_ts_out
        description: path/filename for user physics time series output
      std_biology:
        value: timeseries/std_bio_2025_bloomcast.out
        variable_name: std_bio_ts_out
        description: path/filename for standard biology time series output
      user_biology:
        value: timeseries/user_bio_2025_bloomcast.out
        variable_name: user_bio_ts_out
        description: path/filename for user biology time series output
      std_chemistry:
        value: timeseries/std_chem_2025_bloomcast.out
        variable_name: std_chem_ts_out
        description: path/filename for standard chemistry time series output
      user_chemistry:
        value: timeseries/user_chem_2025_bloomcast.out
        variable_name: user_chem_ts_out
        description: path/filename for user chemistry time series output

    ...

    profile_file_base:
      value: profiles/2026_bloomcast
      variable_name: profilesBase_fn
      description: path/filename base for profiles (datetime will be appended)
    user_profile_file_base:
      value: profiles/user_2026_bloomcast
      variable_name: userprofilesBase_fn
      description: path/filename base for user profiles (datetime appended)
    halocline_file:
      value: profiles/halo_2026_bloomcast.out
      variable_name: haloclines_fn
      description: path/filename for halocline results
    hoffmueller_file:
      value: profiles/hoff_2026_bloomcast.out
      variable_name: Hoffmueller_fn
      description: path/filename for Hoffmueller results
    user_hoffmueller_file:
      value: profiles/user_hoff_2026_bloomcast.out
      variable_name: userHoffmueller_fn
      description: path/filename for user Hoffmueller results

    ...

    hoffmueller_start_year:
      value: 2025
      variable_name: Hoff_startyr
      description: year to start Hoffmueller results output

    ...

    hoffmueller_end_year:
      value: 2026
      variable_name: Hoff_endyr
      description: year to end Hoffmueller results output

Edit the :file:`run/config.yaml` file to point to the year's infile via the :kbd:`ensemble[base_infile]` item:

.. code-block:: yaml

    ...

    ensemble:
      ...
      base_infile: 2026_bloomcast_infile.yaml

    ...


Run the model ensemble with:

.. code-block:: bash

    pixi run bloomcast ensemble -v config.yaml --debug
