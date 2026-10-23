# ZEN-europe


Data for the European, sector-coupled energy system model.

ZEN-europe generates the input data of a European energy system model for
[ZEN-garden](https://github.com/ZEN-universe/ZEN-garden), built on
[ZEN-creator](https://zen-creator.readthedocs.io/en/latest/). It covers 28
countries at NUTS0 resolution and 15 sectors, from electricity and heat to
steel, cement, chemicals and transport.

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