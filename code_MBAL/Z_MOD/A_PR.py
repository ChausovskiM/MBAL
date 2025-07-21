def A_PR(P, T, XiRange, Pc, Tc, w, Vc):
    """
    Расчёт параметра A для всей газовой смеси в PR-уравнении состояния.

    Параметры:
    - P (float): давление, Па
    - T (float): температура, K
    - XiRange (list): молярные доли компонентов, %
    - Pc, Tc (list): критическое давление и температура компонентов (МПа, K)
    - w (list): ацентрические факторы
    - Vc (list): критические объёмы (см³/моль)

    Возвращает:
    - A (float): суммарный параметр A для смеси
    """
    A = 0.0
    n = len(XiRange)
    for i in range(n):
        xi = XiRange[i] / 100
        for j in range(n):
            xj = XiRange[j] / 100
            A += xi * xj * Aij_PR(P, T, i, j, Pc, Tc, w, Vc)
    return A
