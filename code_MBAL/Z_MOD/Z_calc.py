import json
import pandas as pd
import numpy as np
#
from code_MBAL.Z_MOD.Z_GUR import Z_GUR
from code_MBAL.Z_MOD.Z_PR import Z_PR
from code_MBAL.Z_MOD.Z_BB import Z_BB


def calc_mixture_params(gas_components):
    """
    Вычисляет средние параметры смеси: молекулярный вес, критическую температуру и давление.

    Ожидается, что mol_fraction_pct передаётся в процентах (%).
    """
    Mw_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Mw"] for comp in gas_components)
    Tc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Tc"] for comp in gas_components)
    Pc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Pc"] for comp in gas_components)

    return Mw_mix, Tc_mix, Pc_mix

def prepare_inputs_from_components(gas_components):
    """
    Преобразует список компонентов газа в набор входных параметров
    для функции Z_PR: XiRange, Pc, Tc, Vc, w

    Параметры:
    - gas_components (list[dict]): список словарей с параметрами компонентов

    Возвращает:
    - XiRange, Pc, Tc, Vc, w (все списки float)
    """
    gas_components = pd.DataFrame(gas_components)

    XiRange = gas_components['mol_fraction_pct']
    MwRange = gas_components['Mw']
    TcRange = gas_components['Tc']
    PcRange = gas_components['Pc']
    VcRange = gas_components['Vc']
    ZcRange = gas_components['Zc']
    wRange = gas_components['w']

    return XiRange,MwRange,TcRange,PcRange,VcRange,ZcRange,wRange 

def Z_calc(Z_method,Pxb,Tn):

    with open(r"code_sheets\PVT\gas_components.json", 'r', encoding='utf-8') as f:
        gas_components = json.load(f)
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
