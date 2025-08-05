from alfa_1 import alfa_1

def Tust(Tzab, Tair, D, Tw):
    """
    Расчёт устьевой температуры на основе охлаждения потока.

    Параметры:
    - Tzab (float): температура на забое, °C
    - Tair (float): температура воздуха, °C
    - D (float): диаметр трубы, мм
    - Tw (float): время транспортировки, ч

    Возвращает:
    - Tust (float): устьевая температура, °C
    """
    a = alfa_1(D)
    return Tair + (Tzab - Tair) * pow(2.71828, -a * Tw)
