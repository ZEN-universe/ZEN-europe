from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from zen_creator.utils.settings import SettingsCategory

if TYPE_CHECKING:
    from zen_creator.utils.config import Config

logger = logging.getLogger(__name__)


class TimeSettings(SettingsCategory):
    """Time-horizon settings."""

    name: ClassVar[str] = "time"
    controls: ClassVar[dict[str, str]] = {
        "reference_year": "system.reference_year",
        "interval_between_years": "system.interval_between_years",
    }

    reference_year: int = 2026
    last_year: int = 2050
    price_year: int = 2025
    time_series_year: int = 2019
    interval_between_years: int = 2

    def apply(self, config: "Config") -> None:
        """Write the horizon into the system config.

        `optimized_years` follows from the horizon and the interval between
        years, so it is derived here rather than configured separately.
        """
        super().apply(config)
        config.system.optimized_years = self.optimized_years

    @property
    def optimized_years(self) -> int:
        """The number of years ZEN-garden optimizes."""
        span = self.last_year - self.reference_year
        if span % self.interval_between_years:
            last_optimized = (
                self.reference_year
                + span // self.interval_between_years * self.interval_between_years
            )
            logger.warning(
                f"The horizon {self.reference_year}-{self.last_year} is not a "
                f"multiple of the interval of {self.interval_between_years} "
                f"years, so the last optimized year is {last_optimized}."
            )
        return span // self.interval_between_years + 1

    @property
    def years(self) -> list[int]:
        """Every calendar year of the horizon, used to index the written data."""
        return list(range(self.reference_year, self.last_year + 1))
