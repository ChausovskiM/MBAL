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
    if a == 0:
        return 0.0
    else:
        a1 = b
        b1 = a
        c1 = -((ppl) - (pzab)) * ld
        discriminant = (b1) ** 2 - 4 * a1 * c1

        # Проверяем дискриминант
        if discriminant < 0:
            return 0.0

        # Дебит газа
        q = (-b1 + math.sqrt(discriminant)) / (2 * a1)

        # Дебит только положительный
        if q < 0:
            q = 0.0

        return q
