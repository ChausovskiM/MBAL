from code_MBAL.Z_MOD.Z_GUR import Z_GUR
from code_MBAL.Z_MOD.Z_PR import Z_PR
from code_MBAL.Z_MOD.Z_BB import Z_BB
from code_MBAL.common.gas_mixture import (
    calc_mixture_params,
    load_gas_components,
    prepare_inputs_from_components,
)

def Z_calc(Z_method,Pxb,Tn):
    gas_components = load_gas_components()
    XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange,wRange = prepare_inputs_from_components(gas_components)
    Mw_mix, Tc_mix, Pc_mix = calc_mixture_params(gas_components)

    #Z_calc(ZCOR, Pxa, Tn, Pkri, Tkri)
    if Z_method == 'beggs и brill':
        Z_calc = Z_BB(Pxb,Tn, Pc_mix, Tc_mix)
    elif Z_method == 'латонов-гуревич':
        Z_calc = Z_GUR(Pxb,Tn, Pc_mix, Tc_mix)
    elif Z_method == 'пенг-робинсон':
        Z_calc = Z_PR(Pxb,Tn, XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange, wRange)
    else:
        raise ValueError(f"Unknown method calculete Z-factor: '{Z_method}'")
    return Z_calc
