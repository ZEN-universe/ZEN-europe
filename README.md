# ZEN-europe

[![GitHub release](https://img.shields.io/github/v/release/ZEN-universe/ZEN-europe)](https://github.com/ZEN-universe/ZEN-europe/releases)
[![Tests](https://github.com/ZEN-universe/ZEN-europe/actions/workflows/run_tests.yml/badge.svg?branch=main)](https://github.com/ZEN-universe/ZEN-europe/actions/workflows/run_tests.yml)
[![Code Quality Checks](https://github.com/ZEN-universe/ZEN-europe/actions/workflows/format_lint_typecheck.yml/badge.svg?branch=main)](https://github.com/ZEN-universe/ZEN-europe/actions/workflows/format_lint_typecheck.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Documentation Status](https://readthedocs.org/projects/zen-europe/badge/?version=latest)](https://zen-europe.readthedocs.io/en/latest/)

ZEN-europe generates the input data of a European energy system model for
[ZEN-garden](https://github.com/ZEN-universe/ZEN-garden), built on
[ZEN-creator](https://zen-creator.readthedocs.io/en/latest/). It covers 28
countries at NUTS0 resolution and 15 sectors, from electricity and heat to
steel, cement, chemicals and transport.

The model is documented on [Read the Docs](<https://zen-europe.readthedocs.io/en/latest/>)

## Quick start

```bash
conda env create -f zen_europe_env.yml
conda activate zen-europe-env

# generate the default dataset from the folder that contains data/raw_data
zen-europe

# generate every variant declared in a models file
zen-europe --config_path ./my_config.yaml --all
```

The dataset is written to `./data/<name>`, together with the ZEN-garden
configuration `./data/config.yaml`.

## Documentation

More complete documentation is available on the 
[Read the Docs page](https://zen-europe.readthedocs.io/en/latest/).