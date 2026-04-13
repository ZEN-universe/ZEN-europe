from pathlib import Path

from zen_creator import Model


def run(config: Path | str) -> None:

    # Get path to crystal ball model
    zen_europe_package_dir = Path(__file__).resolve().parent
    crystal_ball_path = zen_europe_package_dir / "input" / "crystal_ball"

    # load crystal ball model as starting point
    # TODO: this should be remove in the long run and replaced
    # with model.from_config()
    model = Model.from_existing(crystal_ball_path, config=config)

    # apply changes
    model.build()

    # save model output
    model.write()
