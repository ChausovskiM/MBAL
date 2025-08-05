import json
import pandas as pd
import numpy as np
#

from code_MBAL.Z_MOD.Z_calc import Z_calc
from code_MBAL.Density_MOD.Density_calc import Density_calc
from code_MBAL.Visc_MOD.Visc_calc import Visc_calc
from code_MBAL.Visc_MOD.Visc_JST import Visc_JST
from code_MBAL.Visc_MOD.Visc_Lee_Gonzalez import Visc_Lee_Gonzalez



def Ld(
    z_method: str,
    density_method: str,
    viscosity_method: str,
    p_mpa: float,
    t_c: float,
) -> float:
    """
    Рассчитывает функцию подвижности (Ld) для газа.

    Параметры:
    -----------
    z_method : str Метод расчета коэффициента сжимаемости (например, "Peng-Robinson").
    density_method : str Метод расчета плотности (например, "Correlation").
    viscosity_method : str Метод расчета вязкости (например, "Jossi-Stiel-Thodos").
    p_mpa : float Давление, МПа.
    t_c : float Температура, °C.
    p_crit : float Критическое давление, МПа.
    t_crit : float Критическая температура, °C.
    m : float Молярная масса газа, кг/кмоль.

    Возвращает:
    -----------
    float
        Значение функции подвижности.
    """
    #
    #Mw_mix, Tc_mix, Pc_mix = calc_mixture_params(gas_components)
    #XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange,wRange = prepare_inputs_from_components(gas_components)
    # Расчет коэффициента сжимаемости (Z)
    z = Z_calc(z_method,p_mpa,t_c)
    
    # Расчет плотности
    #rho0 = Mw_mix / 24.04  # нормальная плотность, кг/м³
    #density = rho0 * p_mpa*10**6 * 293.15 / (101325 * (t_c+273.15) * z) #строка 12

    density = Density_calc(density_method, p_mpa, t_c, z)
    # Расчет вязкости
    viscosity = Visc_calc(viscosity_method, p_mpa, t_c, z, density)
    # if viscosity_method == 'jossi stiel thodos':
    #     viscosity = Visc_JST(p_mpa, t_c, z, XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange)/1000
    # elif viscosity_method == 'lee-gonzalez':
    #     viscosity = Visc_Lee_Gonzalez(t_c,density, Mw_mix) / 1000

    
    # Расчет функции подвижности
    ld = p_mpa / z / viscosity
    
    return ld