from scipy.interpolate import CubicSpline

def Ld_tab(P_MPA, pressure_data, ld_data):
    """
    Интерполяция/экстраполяция гидравлической длины по табличным данным.

    Параметры:
    - P_MPA (float): давление, МПа
    - pressure_data (list): давления (МПа)
    - ld_data (list): гидравлические длины (безразмерные)

    Возвращает:
    - Ld (float): расчётная гидравлическая длина
    """
    if len(pressure_data) < 2:
        raise ValueError("Недостаточно данных для интерполяции")

    spline = CubicSpline(pressure_data, ld_data, extrapolate=True)
    return float(spline(P_MPA))
