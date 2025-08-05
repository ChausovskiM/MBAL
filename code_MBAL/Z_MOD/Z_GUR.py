import math
def Z_GUR(P_MPA, T_C, Pkri_MPa, Tkri_K):
    """
    Расчёт коэффициента сверхсжимаемости Z по корреляции GUR.

    Параметры:
    - P_MPA (float): давление, МПа
    - T_C (float): температура, °C
    - Pkri_MPa (float): критическое давление, МПа
    - Tkri_K (float): критическая температура, K

    Возвращает:
    - Z (float): коэффициент сверхсжимаемости
    """
    P_Pa = P_MPA * 1e6
    T_K = T_C + 273.15
    Pkr = Pkri_MPa * 1e6

    Ppr = P_Pa / Pkr
    Tpr = T_K / Tkri_K

    Z = (0.4 * math.log10(Tpr) + 0.73) ** Ppr + 0.1 * Ppr
    return Z