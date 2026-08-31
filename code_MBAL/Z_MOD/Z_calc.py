from code_MBAL.Z_MOD.Z_BB import Z_BB
from code_MBAL.Z_MOD.Z_GUR import Z_GUR
from code_MBAL.Z_MOD.Z_PR import Z_PR
from code_MBAL.Z_MOD.Z_tab import Z_tab
from code_MBAL.common.gas_mixture import (
    calc_mixture_params,
    load_gas_components,
    prepare_inputs_from_components,
)


def Z_calc(Z_method, Pxb, Tn, pressure_data=None, z_data=None):
    method = Z_method.strip().lower()

    if method == 'таблица':
        if pressure_data is None or z_data is None:
            raise ValueError("Не переданы pressure_data и z_data для Z_tab")
        return Z_tab(Pxb, pressure_data, z_data)

    gas_components = load_gas_components()
    inputs = prepare_inputs_from_components(gas_components)
    XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange, wRange = inputs
    _, Tc_mix, Pc_mix = calc_mixture_params(gas_components)

    if method == 'beggs и brill':
        return Z_BB(Pxb, Tn, Pc_mix, Tc_mix)
    if method == 'латонов-гуревич':
        return Z_GUR(Pxb, Tn, Pc_mix, Tc_mix)
    if method == 'пенг-робинсон':
        return Z_PR(
            Pxb, Tn, XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange, wRange
        )
    raise ValueError(f"Unknown method calculete Z-factor: '{Z_method}'")
