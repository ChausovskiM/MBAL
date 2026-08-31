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
    pressure_drop = Ppl**2 - Pzab**2
    if A == 0 or pressure_drop <= 0:
        return 0.0

    if b == 0:
        return max(pressure_drop / A, 0.0)

    A1 = b
    B1 = A
    C1 = -pressure_drop

    D = B1**2 - 4 * A1 * C1

    if D < 0:
        return 0.0

    Q = (-B1 + math.sqrt(D)) / (2 * A1)
    return max(Q, 0.0)
