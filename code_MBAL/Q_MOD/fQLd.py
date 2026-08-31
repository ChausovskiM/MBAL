import math

def fQLd(a: float, b: float, ld: float, ppl: float, pzab: float) -> float:
    """
    Расчет дебита газа по уравнению (Рпл-Рзаб)*Ld=АQ+ВQ2

    Параметры:
    a (float): Коэффициент A
    b (float): Коэффициент B
    ld (float): Коэффициент Ld
    ppl (float): Давление пластовое
    pzab (float): Давление забойное

    Возвращает:
    float: Дебит газа
    """
    pressure_drop = (ppl - pzab) * ld
    if a == 0 or pressure_drop <= 0:
        return 0.0

    if b == 0:
        return max(pressure_drop / a, 0.0)

    a1 = b
    b1 = a
    c1 = -pressure_drop
    discriminant = b1**2 - 4 * a1 * c1

    if discriminant < 0:
        return 0.0

    return max((-b1 + math.sqrt(discriminant)) / (2 * a1), 0.0)
