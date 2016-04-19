Network Testing of userspace applications
=========================================

Some userspace applications have issues when working in IPv6-only or
dual-stack (IPv4 and IPv6) environment. Some components provide two
versions of a binary, one for IPv4 and another for IPv6. Purpose of this
project is to map available features and behavior of various applications
in different network-configuration scenarios. To be able to achieve the goal,
the project provides also a test suite able to determine the behavior of
a specifric application.

.. note::
    Currently we are focusing on testing of client/server applications.
    Testing and development is done on `Fedora`_, however we are open to
    accept patches to make the test suite work also on other distributions.

If you are interested in details, please continue with reading.

Contents:

.. toctree::
   :maxdepth: 2

   scenarios
   contributing


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Fedora: https://fedoraproject.org

