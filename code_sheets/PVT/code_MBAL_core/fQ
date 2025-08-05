import math

def fQ(A, b, Ppl, Pzab):
    """
    Расчёт дебита газа по уравнению квадратичного притока.

    Параметры:
    - A (float): линейный коэффициент
    - b (float): квадратичный коэффициент
    - Ppl (float): пластовое давление, МПа
    - Pzab (float): забойное давление, МПа

    Возвращает:
    - Q (float): дебит газа, м³/сут
    """
    if A == 0:
        return 0.0

    A1 = b
    B1 = A
    C1 = -(Ppl**2 - Pzab**2)

    D = B1**2 - 4 * A1 * C1

    if D < 0:
        return 0.0

    Q = (-B1 + math.sqrt(D)) / (2 * A1)
    return max(Q, 0.0)
