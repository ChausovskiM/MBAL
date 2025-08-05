import json
import pandas as pd
import numpy as np
#
from code_MBAL.Visc_MOD.Visc_JST import Visc_JST
from code_MBAL.Visc_MOD.Visc_Lee_Gonzalez import Visc_Lee_Gonzalez
from code_MBAL.Visc_MOD.Visc_tab import Visc_tab

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

def Visc_calc(Metod, P_MPA, T_C, Z, density, pressure_data=None, visc_data=None):
    """
    Универсальная оболочка расчёта динамической вязкости газа.

    Параметры:
    - Metod (str): метод расчёта ('Jossi Stiel Thodos', 'Lee-Gonzalez', 'таблица')
    - P_MPA (float): давление, МПа
    - T_C (float): температура, °C
    - Z (float): коэффициент сверхсжимаемости
    - density (float): плотность газа, кг/м³
    - m (float): относительная молекулярная масса
    - pressure_data, visc_data: табличные данные (если метод 'таблица')

    Возвращает:
    - μ (float): динамическая вязкость газа, Па·с
    """
    # открываем компоненты с листа PVT
    with open(r"code_sheets\PVT\gas_components.json", 'r', encoding='utf-8') as f:
        gas_components = json.load(f)
    XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange,wRange = prepare_inputs_from_components(gas_components)
    Mw_mix, Tc_mix, Pc_mix = calc_mixture_params(gas_components)

    metod = Metod.strip().lower()

    if P_MPA == 0:
        return 0.0
    
    if metod == 'jossi stiel thodos':
        viscosity = Visc_JST(P_MPA, T_C, Z, XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange)/1000
    elif metod == 'lee-gonzalez':
        viscosity = Visc_Lee_Gonzalez(T_C,density, Mw_mix) / 1000
    elif metod == 'таблица':
        if pressure_data is None or visc_data is None:
            raise ValueError("Не переданы табличные данные для Visc_tab")
        return Visc_tab(P_MPA, pressure_data, visc_data) / 1000        
    else:
        raise ValueError(f"Unknown method calculete viscosity: '{Metod}'")

    return viscosity