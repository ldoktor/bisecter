==================
Contribution guide
==================

.. note::

   Except where otherwise indicated in a given source file, all original
   contributions to Avocado are licensed under the GNU General Public
   License version 2 `(GPLv2) <https://www.gnu.org/licenses/gpl-2.0.html>`_
   or any later version.

   By contributing you agree with: a) our code of conduct; b) that these
   contributions are your own (or approved by your employer), and c) you grant
   a full, complete, irrevocable copyright license to all users and developers
   of the Run-perf project, present and future, pursuant to the license of the
   project.


Generally one should follow the usual principles known in the open source
projects like mentioned in http://www.contribution-guide.org/, still
allow me to explicitly mention the most useful advices or specifics of
this project.

First of all **Always assume good intentions**.

Reporting Bugs/Enhancments
==========================

Please use the `Issues <https://github.com/distributed-system-analysis/bisecter/issues>`_
tab on github to report a bug or suggest an enhancement, there are templates
that should simplify the process while making sure all important information
are stored for the future reference or reproducibility.

First time contribution
=======================

.. _clone-and-deploy:

Clone and deploy
----------------

Bisecter is a Python3 project, the simplest way to start hacking on it is to::

    git clone https://github.com/ldoktor/bisecter.git
    cd bisecter
    python3 setup.py develop --user

.. note::
   you might need to add `~/.local/bin` to your bash `PATH` environment
   to make the scripts available in your environment.

Which creates an `egg link` under the ``~/.local/lib/python3*/site-packages/``
directory, which makes python to use the libraries in your clonned directory
instead of the system ones. This means any change to your sources will be
propagated to any new execution for your user.

Develop your feature
--------------------

We are using github pull request to accept changes, the usual workflow is:

1. go to https://github.com/ldoktor/bisecter
2. on the right side click ``fork`` and select under which organization
   you intend to clone it.
3. add this fork to your local git by ``git remote add $name https://github.com/$name/bisecter``
   (replacing the `$name` with your github username/organization)
4. checkout a new branch by ``git checkout -b $headline`` (replacing the
   `$headline` with a suitable short description of what you intend to do) 
5. develop your code; use comments and docstrings; don't forget documentation
   and tests.
6. prepare the patches using ``git commit -as``; don't forget to add new files
   via ``git add``, use sensible commit messages and split the patches to make
   reviewing easier (usually if you need to use `and` or `also` in the commit
   message it's time to split the commit). Allow me to suggest ``git cola``
   for that.
7. commit them to your repo via ``git push $name HEAD`` optionally followed
   by ``-f`` to force-override the changes (again, replace `$name` with you)
#. go to https://github.com/ldoktor/bisecter where a new
   ``Compare & pull request`` button listing your new branch should appear
   (alternatively you can go to your fork, select your branch and use the
   ``Pull request`` button from there.
#. describe your changes, consider including your motivation and examples
   and create the PR.
#. wait for the CI to finish and address all possible issues (or directly
   ask someone for a help, failing PRs will **not** be reviewed).
#. wait for a review, in case of a ``request for a change`` address all issues
   (even if just as a comment explaining why not to change that) and repeat
   steps 5-7 using the ``-f`` to override the changes when committing and
   do include a comment describing the changes you made.

   
Reviewer process
================

**Anyone is welcome to review the patches**, no affiliation to bisecter or any
organization is needed, but in the end one needs to gain an ack from someone
with a write access to the repo. Having an extra review can speedup the process,
though.

.. warning:: Developer is responsible to conform to the contibution guide, but
   it's the **reviewer** who **is responsible** for the code that is being
   merged.

#. Check the CI status, merging anything that would break CI is not allowed
#. Check the ``Signed-off`` line is present in all commits
#. Check the license header and copyright of the new files
#. Review all commit messages, see whether they tell a complete story
#. Thoroughly review all individual changes, test them even one by one if
   in doubt as each commit has to be applicable standalone (to make reverts
   easier)
#. Check there are no regressions introduced
#. Commit the code upstream using ``git merge -S`` to sign the merge commit
   using their gpg signature.

During this process take notes and add them to your review. It's better to
be verbose to avoid unnecessary actions or harm, we don't see each others
and one incorrect sentence can ruin one's day.
