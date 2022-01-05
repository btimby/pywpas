.. image:: https://coveralls.io/repos/github/btimby/pywpas/badge.svg?branch=master
    :target: https://coveralls.io/github/btimby/pywpas?branch=master

.. image:: https://github.com/btimby/pywpas/actions/workflows/ci.yml/badge.svg
    :target: https://github.com/btimby/pywpas/actions

.. image:: https://badge.fury.io/py/pywpas.svg
    :target: https://badge.fury.io/py/pywpas

pywpas
======

A python library to control wpa_supplicant via it's control socket.

Installation
------------

``pip install pywpas``

Example
-------

.. code-block:: python

    import time
    import pywpas
    # sock_path below is the default and can be omitted.
    ctrl = pywpas.Control(sock_path='/var/run/wpa_supplicant)

    # You can get a list of interface names:
    interface_names = ctrl.interface_names()
    print(interface_names)

    # You can iterate over instances of the Interface class:
    for interface in ctrl.interfaces:
        print(interface.name)
    
    # You can get a specific Interface instance by name:
    interface = ctrl.interface(interface_names[0])
    print(interface.status())

    # You can scan for networks available on an interface:
    interface.scan()
    # You might wait a few seconds...
    time.sleep(5.0)
    scan_results = interface.results()

    for network in scan_results:
        print(network.ssid, network.signal_level)

    # You can connect to a network (implictly adds a profile):
    interface.connect(scan_results[0])
    # Write the network to the wpa_supplicant.conf file:
    interface.save_config()
    # Then disconnect...
    interface.disconnect()
    # and remove the network:
    interface.remove_network(scan_results[0])
    # Or remove ALL networks:
    interface.remove_networks()
    interface.save_config()

    # You can also add a profile (without connecting):
    interface.add_network(scan_results[0])
    # And save it:
    interface.save_config()

    # You can define a network and connect to it:
    network = pywpas.Network(ssid='FOOBAR', ...)
    interface.connect(network)
    interface.disconnect()

    # There is a high-level scan function, it will invoke callback
    # with each unique network found during the scan timeout duration:
    scan = interface.background_scan(lambda network: print(network.ssid),
                                     timeout=30.0)
    time.sleep(5.0)
    scan.stop()

wpa_supplicant configuration
----------------------------

You must configure wpa_supplicant to open a control socket. Optionally you can
enable config file writing.

.. code-block:: bash

    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=nobody
    update_config=1

Event with an emtpy configuation (no networks) you can use this library to add
networks, connect to networks and save the profiles to the configuration file.

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