import math

def Z_BB(P_MPA, T_C, Pkri_MPa, Tkri_K):
    import math
    """
    Расчёт коэффициента сверхсжимаемости Z по корреляции Beggs & Brill.

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
    Pkri = Pkri_MPa * 1e6

    Ppr = P_Pa / Pkri
    Tpr = T_K / Tkri_K

    A = 1.39 * math.sqrt(Tpr - 0.92) - 0.36 * Tpr - 0.1
    e = 9 * (Tpr - 1)
    b = (0.62 - 0.23 * Tpr) * Ppr \
        + (0.066 / (Tpr - 0.86) - 0.037) * Ppr ** 2 \
        + 0.32 * Ppr ** 2 / 10 ** e
    C1 = 0.132 - 0.32 * math.log10(Tpr)
    f = 0.3106 - 0.49 * Tpr + 0.1824 * Tpr ** 2
    d = 10 ** f

    Z = A + (1 - A) / math.exp(b) + C1 * Ppr ** d
    return Z
