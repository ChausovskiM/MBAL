# def OGR(Pi_MPA, Pnk_MPA, DataRange):
#     """
#     Расчёт газового фактора по полиному давления.

#     Параметры:
#     - Pi_MPA (float): текущее давление, МПа
#     - Pnk_MPA (float): давление насыщения, МПа
#     - DataRange (list): коэффициенты полинома

#     Возвращает:
#     - OGR (float): газовый фактор, м³/м³
#     """
#     P = Pnk_MPA if Pi_MPA >= Pnk_MPA else Pi_MPA
#     n = len(DataRange)

#     return sum(DataRange[i] * P ** (n - i - 1) for i in range(n))

import numpy as np

def OGR(Pi_MPA: float, Pnk_MPA: float, coefficients: list[float]) -> float:
    """
    Расчет конденсатогазового фактора (КГФ) в зависимости от давления.
    
    Parameters:
        Pi_MPA: Текущее давление, МПа
        Pnk_MPA: Давление начала конденсации, МПа
        coefficients: Коэффициенты полинома [A, B, C, D, ...], где A — коэффициент при старшей степени.
    
    Returns:
        КГФ (конденсат на 1000 м³ газа)
    """
    pressure = Pnk_MPA if Pi_MPA >= Pnk_MPA else Pi_MPA
    # np.polyval ожидает коэффициенты в порядке от старшей степени к младшей (A, B, C, D → Ax³ + Bx² + Cx + D)
    return np.polyval(coefficients, pressure)


