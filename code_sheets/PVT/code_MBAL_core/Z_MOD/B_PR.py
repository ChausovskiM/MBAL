import Bi_PR
def B_PR(P, T, XiRange, Pc, Tc):
    """
    Расчёт параметра B для всей газовой смеси в PR-уравнении состояния.

    Параметры:
    - P (float): давление, Па
    - T (float): температура, K
    - XiRange (list): молярные доли компонентов, %
    - Pc, Tc (list): критические давления и температуры (МПа, K)

    Возвращает:
    - B (float): параметр B для всей смеси
    """
    B = 0.0
    n = len(XiRange)
    for i in range(n):
        xi = XiRange[i] / 100
        B += xi * Bi_PR(P, T, i, Pc[i], Tc[i])
    return B