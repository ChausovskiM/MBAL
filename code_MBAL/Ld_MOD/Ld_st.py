import math
from Re import Re

def Ld_st(Qgas, d_mm, Mu, Ro, Lk):
    """
    Расчёт гидравлической длины в ламинарном/переходном режиме.

    Параметры:
    - Qgas (float): объёмный расход газа, м³/сут
    - d_mm (float): диаметр трубы, мм
    - Mu (float): вязкость газа, Па·с
    - Ro (float): относительная плотность газа
    - Lk (float): длина участка, м

    Возвращает:
    - Ld (float): гидравлическая длина, безразмерная
    """
    d_m = d_mm / 1000
    Re_val = Re(Qgas, d_mm, Mu, Ro)
    log_term = math.log10(5.62 / Re_val ** 0.9 + 2 * Lk / (d_m * 7.41))
    return 1 / (4 * log_term ** 2)
