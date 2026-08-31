from code_MBAL.Z_MOD.Z_calc import Z_calc

def Velosity(ZCOR, Tpl, Qgas, Pzab, d_mm):
    """
    Расчёт линейной скорости газа в скважине.

    Параметры:
    - ZCOR (str): метод корреляции Z
    - Tpl (float): пластовая температура, °C
    - Qgas (float): дебит газа, тыс. м³/сут
    - Pzab (float): забойное давление, МПа
    - d_mm (float): внутренний диаметр трубы, мм
    - Pkri (float): критическое давление, МПа
    - Tkri (float): критическая температура, °C

    Возвращает:
    - V (float): линейная скорость газа, м/с
    """
    if Qgas <= 0 or Pzab <= 0 or d_mm <= 0:
        return 0.0

    Zpl = Z_calc(ZCOR, Pzab, Tpl)
    T_K = Tpl + 273.15
    d_cm = d_mm / 10

    return 0.52 * T_K * Zpl * Qgas / (Pzab * 10 * d_cm ** 2)
