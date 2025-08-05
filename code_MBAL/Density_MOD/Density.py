import json
import pandas as pd

def calc_mixture_params(gas_components):
    """
    Вычисляет средние параметры смеси: молекулярный вес, критическую температуру и давление.

    Ожидается, что mol_fraction_pct передаётся в процентах (%).
    """
    Mw_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Mw"] for comp in gas_components)
    Tc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Tc"] for comp in gas_components)
    Pc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Pc"] for comp in gas_components)

    return Mw_mix, Tc_mix, Pc_mix

def Density(P_MPA, T_C, Z):
    """
    Аналитический расчёт плотности газа.

    Параметры:
    - P_MPA (float): давление, МПа
    - T_C (float): температура, °C
    - Z (float): коэффициент сжимаемости
    - m (float): относительная молекулярная масса

    Возвращает:
    - ρ (float): плотность газа, кг/м³
    """
    with open(r"code_sheets\PVT\gas_components.json", 'r', encoding='utf-8') as f:
        gas_components = json.load(f)
    #
    Mw_mix, Tc_mix, Pc_mix = calc_mixture_params(gas_components)
    P = P_MPA * 1e6  # Па
    T = T_C + 273.15  # K

    rho0 = Mw_mix / 24.04  # нормальная плотность, кг/м³
    rho = rho0 * P * 293.15 / (101325 * T * Z)

    return rho