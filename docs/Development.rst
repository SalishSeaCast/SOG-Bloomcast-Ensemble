.. _Development:

Development
===========

.. _DevelopmentAndDeploymentEnvironment:

Development and Deployment Environment
--------------------------------------

Development and :ref:`Deployment` of the ensemble bloomcast system is done in an `Anaconda`_ Python 3 `conda`_ environment.

.. _Anaconda: http://docs.continuum.io/anaconda/index.html
.. _conda: http://conda.pydata.org/docs/intro.html

Create a new :program:`conda` environment with Python 3 and :program:`pip` installed in it,
and activate the environment:

.. code-block:: bash

    $ conda create -n bloomcast python=3 pip

    ...

    $ source activate bloomcast

When this was written in Feb-2015 this results the installation of Python 3.4.2,
pip 6.0.8,
and setuptools 12.1.

Our first choice for installing packages is the :program:`conda` installer because it uses pre-built binary packages so it is faster and avoids problems that can arise with compilation of C extensions that are part of some of the packages.
Unfortunately,
not all of the packages that we need are available in the :program:`conda` repositories so we use :program:`pip` to install those from the `Python Package Index`_ (PyPI).

.. _Python Package Index: https://pypi.python.org/pypi

Install the packages that bloomcast depends on:

.. code-block:: bash

    (bloomcast)$ conda install matplotlib pyyaml requests sphinx
    (bloomcast)$ pip install arrow beautifulsoup4 cliff mako sphinx-bootstrap-theme

Install the :ref:`SOG_CommandProcessor-section` and bloomcast as editable packages so that changes in files within those packages are immediately reflected in the installation environment.
Assuming that the :kbd:`SOG` and :kbd:`SoG-bloomcast` repos have been cloned into a :file:`SOG-projects/` directory in your workspace,
the installation commands are:

.. code-block:: bash

    (bloomcast)$ cd SOG-projects/
    (bloomcast)$ cd SOG/
    (bloomcast)$ pip install --editable SOG
    (bloomcast)$ pip install --editable SoG-bloomcast

For a development environment also install some testing and debugging tools:

.. code-block:: bash

    (bloomcast)$ conda install coverage ipython pytest
    (bloomcast)$ pip install ipdb
