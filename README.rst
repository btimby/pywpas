.. image:: https://coveralls.io/repos/github/smartfile/pywpas/badge.svg?branch=master
    :target: https://coveralls.io/github/smartfile/pywpas?branch=master

.. image:: https://github.com/btimby/pywpas/actions/workflows/ci.yml/badge.svg
    :target: https://github.com/btimby/pywpas/actions

.. image:: https://badge.fury.io/py/pywpas.svg
    :target: https://badge.fury.io/py/pywpas

pywpas
==================

A python library to control wpa_supplicant via it's control socket.

Installation
------------

``pip install pywpas``

Example:

.. code-block:: python

    import pywpas

wpa_supplicant
--------------

You must configure wpa_supplicant to open a control socket. Optionally you can
enable config file writing.

.. code-block:: bash

    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=nobody
    update_config=1

Development
-----------

To deploy to PyPI:

::

    git tag <version>
    git push --tags

CI will do the rest.

Tests and linting:

::

    make test
    make lint