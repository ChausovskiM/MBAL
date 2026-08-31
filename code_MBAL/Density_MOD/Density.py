from code_MBAL.common.gas_mixture import calc_mixture_params, load_gas_components


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
    Mw_mix, _, _ = calc_mixture_params(load_gas_components())
    P = P_MPA * 1e6  # Па
    T = T_C + 273.15  # K

    rho0 = Mw_mix / 24.04  # нормальная плотность, кг/м³
    rho = rho0 * P * 293.15 / (101325 * T * Z)

    return rho
