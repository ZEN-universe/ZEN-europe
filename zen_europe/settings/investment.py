from typing import ClassVar

from zen_creator.utils.settings import SettingsCategory


class InvestmentSettings(SettingsCategory):
    """Investment and capacity settings."""

    name: ClassVar[str] = "investment"
    controls: ClassVar[dict[str, str]] = {
        "allow_investment": "system.allow_investment",
        "knowledge_depreciation_rate": "system.knowledge_depreciation_rate",
        # We don't set "system.use_capacities_existing" here because it would overwrite
        # the existing hydro capacities even if use_existing_capacities is False.
        # We already remove all existing capacities in the model if
        # use_existing_capacities is False, so we don't need to set this control.
    }

    allow_investment: bool = True
    use_existing_capacities: bool = True
    # keeps the existing hydro capacities even if use_existing_capacities is False
    keep_existing_hydro_capacities: bool = False
    use_existing_oil_to_x_capacities: bool = False
    use_construction_times: bool = False
    # takes precedence over cap_nuclear_capacity_to_past_investments
    use_nuclear_phase_out: bool = True
    cap_nuclear_capacity_to_past_investments: bool = True
    use_power_line_capacity_limit: bool = True
    allow_offshore_chemical_pipelines: bool = False
    account_for_offshore_transport: bool = True
    use_battery_e2p_ratio: bool = False
    use_200y_lifetime_hydro: bool = True
    use_diffusion_rates: bool = True
    use_inf_spillover_rate: bool = True
    use_unbounded_market_share: bool = True
    use_unbounded_capacity_addition_carbon: bool = True
    knowledge_depreciation_rate: float = 0.1
    set_future_CCS_investments: bool = False
    consider_carbon_storage_expansion: bool = False
