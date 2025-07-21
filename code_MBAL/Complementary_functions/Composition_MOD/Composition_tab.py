from scipy.interpolate import CubicSpline

def Composition_tab(P_MPA, index, table):
    """
    Интерполяция состава компонента по табличным данным.

    Параметры:
    - P_MPA (float): давление, МПа
    - index (int): индекс компонента (1-based)
    - table (list of list): строки: давление + компоненты

    Возвращает:
    - доля компонента, %
    """
    pressures = [row[0] for row in table]
    values = [row[index] for row in table]

    spline = CubicSpline(pressures, values, extrapolate=True)
    return float(spline(P_MPA))
