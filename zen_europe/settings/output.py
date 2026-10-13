from pathlib import Path
from typing import ClassVar

from zen_creator.utils.settings import SettingsCategory


class OutputSettings(SettingsCategory):
    """Settings controlling where generated datasets are written."""

    name: ClassVar[str] = "output"

    path: Path = Path("data") / "created_models"
