import math

from code_MBAL.Z_MOD.Z_calc import Z_calc
from code_MBAL.Density_MOD.Density_calc import Density_calc
from code_MBAL.Visc_MOD.Visc_calc import Visc_calc


from code_MBAL.Pust_MOD.Ld_MOD.Ld_calc import Ld_calc
from code_MBAL.Pust_MOD.S import S

# мистраль
def Pust(Pzab, Qgas, d, Lk, Ro, L, Tust, Tzab, ZCOR, VCOR, DCOR, LCOR, Ld_tab, H):
    """
    Расчет устьевого давления

    :param Pzab: забойное давление, МПа
    :param Qgas: дебит газа приведенный к стандартным условиям, тыс. м3/сут
    :param d: внутренний диаметр, мм
    :param Lk: абсолютная шероховатость, мм
    :param Ro: относительная плотность газа, д.ед. (Mgas/29)
    :param L: глубина скважины, м
    :param Tust: устьевая температура, град С
    :param Tzab: забойная температура, град С
    :param ZCOR: корреляция коэффициента сверхсжимаемости
    :param VCOR: корреляция для вязкости
    :param DCOR: корреляция для расчета плотности
    :param LCOR: корреляция для расчета коэфф. гидравлического сопротивления
    :param Ld_tab: параметр для расчета коэффициента гидравлического сопротивления
    :param H: параметр для расчета функции S
    :return: устьевое давление, МПа
    """
    numeric_inputs = (Pzab, Qgas, d, Lk, Ro, L, Tust, Tzab, Ld_tab, H)
    try:
        inputs_are_finite = all(math.isfinite(float(value)) for value in numeric_inputs)
    except (TypeError, ValueError):
        return 0.0
    if not inputs_are_finite:
        return 0.0
    if Pzab <= 0 or Qgas <= 0 or d <= 0:
        return 0.0

    try:
        Pbuf = Pzab * 0.5
        Tsr = (Tzab + Tust) / 2
        Psr = (Pzab + Pbuf) / 2
        Zsr = Z_calc(ZCOR, Psr, Tsr)
        Plot = Density_calc(DCOR, Psr, Tsr, Zsr)
        Mu = Visc_calc(VCOR, Psr, Tsr, Zsr, Plot)

        fi = 9.9143 * 1000 * Ld_calc(LCOR, Qgas, d, Mu, Ro, Lk, Ld_tab) * (Zsr ** 2) * ((Tsr + 273.15) ** 2) / ((d / 1000) ** 5) * (math.exp(2 * S(Ro, L, Zsr, Tsr)) - 1)
        radicand = (Pzab * 1e6) ** 2 - fi * (Qgas * 1000 / 24 / 3600) ** 2
        if radicand < 0:
            return 0.0
        result = math.sqrt(radicand / math.exp(2 * S(Ro, H, Zsr, Tsr))) / 1e6
    except (ArithmeticError, OverflowError, TypeError, ValueError):
        return 0.0

    return result if math.isfinite(result) and result > 0 else 0.0
