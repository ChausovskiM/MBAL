from code_MBAL.Visc_MOD.Visc_JST import Visc_JST
from code_MBAL.Visc_MOD.Visc_Lee_Gonzalez import Visc_Lee_Gonzalez
from code_MBAL.Visc_MOD.Visc_tab import Visc_tab
from code_MBAL.common.gas_mixture import (
    calc_mixture_params,
    load_gas_components,
    prepare_inputs_from_components,
)

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
    gas_components = load_gas_components()
    XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange,wRange = prepare_inputs_from_components(gas_components)
    Mw_mix, _, _ = calc_mixture_params(gas_components)

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
