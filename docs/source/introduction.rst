============
Introduction
============

This tool is inspired by the ``git bisect`` tool but allows to bisect over
multiple arbitrary lists of arguments like nightly builds, tool versions or
simply list of arguments.

Setup
=====

Bisecter is available from ``pip`` so one can install it by executing::

    python3 -m pip install bisecter

or to install directly the latest version from git::

    python3 -m pip install git+https://github.com/ldoktor/bisecter.git

Basic usage
===========

The workflow is similar to ``git bisect``, only when starting the bisection
one needs to specify the lists of arguments this bisection is going to use::

    bisecter start '20230101,20230102,20230103,20230104,20230105,20230106,20230107'
    bisecter run ./test.sh
    bisecter log

One can also manually tag variants::

    bisecter start '20230101,20230102,20230103,20230104,20230105,20230106,20230107'
    ./test.sh $(bisecter args)
    bisecter good
    ./test.sh $(bisecter args)
    bisecter bad
    ...

See ``bisecter --help`` for more details.
