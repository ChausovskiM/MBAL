from Ggas import Ggas
from Goil import Goil
from Gt import Gt
from Cp import Cp
from Tw import Tw
from Tust import Tust

def Temp_calc(Qg, RG, Qo, Ro, Cpg, Cpo, D1, D2, D, Tzab, Tair):
    """
    Общий расчёт температурного блока.

    Параметры:
    - Qg (float): объёмный расход газа, м³/сут
    - RG (float): плотность газа, кг/м³
    - Qo (float): объёмный расход нефти, м³/сут
    - Ro (float): плотность нефти, кг/м³
    - Cpg (float): теплоёмкость газа, Дж/(кг·К)
    - Cpo (float): теплоёмкость нефти, Дж/(кг·К)
    - D1, D2 (datetime): метки времени
    - D (float): диаметр трубы, мм
    - Tzab (float): температура на забое, °C
    - Tair (float): температура воздуха, °C

    Возвращает:
    - dict: расчётные параметры (Ggas, Goil, Gt, Cp, Tw, Tust)
    """
    Gg = Ggas(Qg, RG)
    Go = Goil(Qo, Ro)
    Gtotal = Gt(Gg, Go)
    Cp_mix = Cp(Gg, Go, Cpg, Cpo)
    time_well = Tw(D1, D2)
    T_surface = Tust(Tzab, Tair, D, time_well)

    return {
        "Ggas": Gg,
        "Goil": Go,
        "Gt": Gtotal,
        "Cp": Cp_mix,
        "Tw": time_well,
        "Tust": T_surface
    }
