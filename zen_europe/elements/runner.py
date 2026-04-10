from pathlib import Path

from zen_creator import Model

import zen_europe.elements.carriers as _
import zen_europe.elements.energy_systems as _
import zen_europe.elements.conversion_technologies as _
import zen_europe.elements.storage_technologies as _
import zen_europe.elements.transport_technologies as _


def run(conf: Path):

    path_to_crystal_ball = Path("./crystal_ball")
    
    # load crystal ball model as starting point
    # TODO: this should be remove in the long run and replaced 
    # with model.from_config()
    model = Model.from_existing(path_to_crystal_ball)
    
    # apply changes
    model.build()

    # save model output
    model.write()



