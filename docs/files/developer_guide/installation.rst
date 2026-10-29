.. _dev_install.dev_install:

###########################
Installation for Developers
###########################

If you want to work on the codebase, you can fork and clone the repository from
`GitHub <https://github.com/ZEN-universe/ZEN-europe>`_.

If it's your first time using GitHub, register at `<https://github.com/>`_.
After you have created an account, you can fork and clone the repository.

Navigate to `<https://github.com/ZEN-universe/ZEN-europe>`_ on Github and click
on the "Fork" button at the top right corner of the page to create a copy of the
repository under your account and select yourself as the owner.

**Clone your forked repository:**

Clone your forked repository by running the following lines in `Git-Bash
<https://git-scm.com/downloads>`_::

    git clone git@github.com:<your-username>/ZEN-europe.git
    cd ZEN-europe

Substitute ``<your-username>`` with your Github username. If you gave the forked
repository a different name, replace ``ZEN-europe`` with the name of your
repository.

.. note::
    If you get the permissions error "Permission denied (publickey)", you will
    need to create the SSH key. Follow the instructions on `how to generate an
    SSH key <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key>`_
    and then `how to add it to your account <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account#adding-a-new-ssh-key-to-your-account>`_.
    You will not need to add the SSH key to the Agent, so only follow the first
    website until before `Adding your SSH key to the ssh-agent <https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#adding-your-ssh-key-to-the-ssh-agent>`_

**Track the upstream repository:**

In your terminal window, navigate to the root folder of your local ZEN-europe
repository (i.e. the folder where the file ``zen_europe_env.yml`` is
located)::

    cd <path_to_zen_europe_repo>

Track the upstream repository by running the following lines in Git-Bash::

    git remote add upstream https://github.com/ZEN-universe/ZEN-europe.git
    git fetch upstream

**Create the ZEN-europe conda environment:**

Open the Anaconda Prompt application. This is a terminal window provided by
Anaconda which allows you to run Anaconda commands.

In the Anaconda Prompt, change the directory to the root folder of your local
ZEN-europe repository::

  cd <path_to_zen_europe_repo>

Now you can install and activate the conda environment for ZEN-europe with the
following commands::

  conda env create -f zen_europe_env.yml
  conda activate zen-europe-env

The installation may take a couple of minutes. If the installation was
successful, you can see the environment ``zen-europe-env`` at
``C:\Users\<username>\anaconda3\envs`` or wherever Anaconda is installed.

.. note::
    We strongly recommend working with conda environments. The environment
    installs ZEN-europe in editable mode together with the ``dev`` and
    ``docs`` dependencies, so that changes to the code take effect without
    reinstalling. ZEN-creator and all other dependencies are installed from
    PyPI automatically.

**Optional: develop ZEN-creator alongside:**

If you also want to change `ZEN-creator <https://github.com/ZEN-universe/ZEN-creator>`_,
clone it next to ZEN-europe and install it in editable mode into the
activated environment::

  pip install -e <path_to_zen_creator_repo>

ZEN-europe then uses your local copy of ZEN-creator instead of the released
version.

**Check the installation:**

From the root folder of the repository, run the unit tests and generate the
default dataset::

  pytest tests/unit
  zen-europe

The dataset is generated from the raw data in ``./data/raw_data`` (see
:ref:`tutorials.tutorials`). Before opening a pull request, also run the code
quality checks of the continuous integration::

  black .
  ruff check .
  mypy .
