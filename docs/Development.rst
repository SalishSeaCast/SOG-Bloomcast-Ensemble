.. _Development:

Development
===========

.. _DevelopmentAndDeploymentEnvironment:

Development and Deployment Environment
--------------------------------------

Development and :ref:`Deployment` of the ensemble bloomcast system is done using Pixi_.

.. _Pixi: https://pixi.prefix.dev/latest/

Clone the repository from GitHub,
then install the dependencies,
environments,
and the :py:obj:`bloomcast` package:

.. code-block:: bash

    git clone git@github.com:SalishSeaCast/SOG-Bloomcast-Ensemble.git
    cd SOG-Bloomcast-Ensemble
    pixi install

Use :command:`pixi run` to execute commands.
The :py:obj:`bloomcast` package is set up to run in the :file:`run/` directory.
Example:

.. code-block:: bash

    cd run/
    pixi run bloomcast --version
