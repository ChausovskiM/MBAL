from code_MBAL.Z_MOD.Z_calc import Z_calc
from code_MBAL.Density_MOD.Density_calc import Density_calc
import math

def Tochigin(Pz, Tpl, sigma, Ro_lic, d_mm, ZCOR, DCOR,  m):
    """
    Расчёт критической скорости газа по критерию Точигина.

    Параметры:
    - Pz (float): давление на забое, МПа
    - Tpl (float): температура на забое, °C
    - sigma (float): поверхностное натяжение, Н/м
    - Ro_lic (float): плотность жидкости, кг/м³
    - d_mm (float): внутренний диаметр, мм
    - ZCOR (str): метод корреляции Z
    - DCOR (str): метод корреляции плотности
    - Pkri (float): критическое давление газа, МПа
    - Tkri (float): критическая температура газа, °C
    - m (float): относительная молекулярная масса газа

    Возвращает:
    - Vc (float): критическая скорость газа, м/с
    """
    if Ro_lic == 0:
        Ro_lic = 1000

    Z_calculate = Z_calc(ZCOR, Pz, Tpl)
    Ro_gas = Density_calc(DCOR, Pz, Tpl, Z_calculate)

    if Ro_lic - Ro_gas <= 0:
        return 0.0

    numerator = 9.8 * sigma * Ro_lic**2
    denominator = Ro_gas**2 * (Ro_lic - Ro_gas)

    return 3.3 * (numerator / denominator) ** 0.25

