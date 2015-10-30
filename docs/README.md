Ginger S390x Plugin
==============

Ginger S390x is an open source IBM z Systems IO management plugin for Wok
(Webserver Originated from Kimchi), that provides an intuitive web panel with
common tools for configuring and managing the Linux systems.

Wok is a cherrypy-based web framework with HTML5 support that is extended by
plugins which expose functionality through REST APIs.

The current features include:
      IBM z Systems IO Management

Browser Support
===============

Desktop Browser Support:
-----------------------
* **Internet Explorer:** Current version
* **Chrome:** Current version
* **Firefox:** Current version
* **Safari:** Current version
* **Opera:** Current version

Mobile Browser Support:
-----------------------
* **Safari iOS:** Current-1 version
* **Android Browser** Current-1 version

Hypervisor Distro Support
=========================

Ginger S390x and Wok might run on any GNU/Linux distribution that meets the conditions described on the 'Getting Started' section below.

The Ginger community makes an effort to test it with the latest version of KVM for IBM z Systems.

Getting Started
===============

Install Dependencies
--------------------

**KVM for IBM z Systems**

    $ sudo yum install wok

    # These dependencies are only required if you want to run the tests:
    $ sudo yum install python-mock

Build and Install
-----------------

    Wok:
    $ ./autogen.sh --system

    $ make
    $ sudo make install   # Optional if running from the source tree


    Ginger S390x:
    $ cd src/wok/plugins/gingers390x
    $ ./autogen.sh --system

    $ make
    $ sudo make install   # Optional if running from the source tree

Run
---

    $ systemctl start wokd


Test
----

    $ cd src/wok/plugins/gingers390x

    $ make check-local # check for i18n and formatting errors
    $ sudo make check

After all tests are executed, a summary will be displayed containing any
errors/failures which might have occurred.
