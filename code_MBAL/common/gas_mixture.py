from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import pandas as pd


PVT_COMPONENTS_PATH = Path("code_sheets") / "PVT" / "gas_components.json"


@lru_cache(maxsize=None)
def load_gas_components(path: str | Path = PVT_COMPONENTS_PATH) -> list[dict]:
    """Load gas components from JSON file."""
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def calc_mixture_params(gas_components: Iterable[dict]) -> tuple[float, float, float]:
    """Calculate mean molecular weight, critical temperature and pressure."""
    mw_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Mw"] for comp in gas_components)
    tc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Tc"] for comp in gas_components)
    pc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Pc"] for comp in gas_components)
    return mw_mix, tc_mix, pc_mix


def prepare_inputs_from_components(gas_components: Iterable[dict]):
    """Convert gas components list to aligned vectors for EOS/viscosity formulas."""
    gas_df = pd.DataFrame(gas_components)

    xi_range = gas_df["mol_fraction_pct"]
    mw_range = gas_df["Mw"]
    tc_range = gas_df["Tc"]
    pc_range = gas_df["Pc"]
    vc_range = gas_df["Vc"]
    zc_range = gas_df["Zc"]
    w_range = gas_df["w"]

    return xi_range, mw_range, tc_range, pc_range, vc_range, zc_range, w_range
