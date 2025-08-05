from code_MBAL.Pust_MOD.Ld_MOD.Ld_st import Ld_st
from code_MBAL.Pust_MOD.Ld_MOD.Ld_turb import Ld_turb
from code_MBAL.Pust_MOD.Ld_MOD.Ld_tab import Ld_tab

def Ld_calc(LCOR, Qgas, d_mm, Mu, Ro, Lk, Ld_tab_value):
    """
    Универсальная оболочка расчёта гидравлической длины.

    Параметры:
    - LCOR (str): метод расчёта ('cтандартная зависимость', 'турбулентный', 'таблица')
    - Qgas (float): расход газа, м³/сут
    - d_mm (float): диаметр трубы, мм
    - Mu (float): вязкость газа, Па·с
    - Ro (float): относительная плотность газа
    - Lk (float): длина участка трубы, м
    - Ld_tab_value (float): табличное значение длины, м

    Возвращает:
    - Ld (float): расчётная гидравлическая длина
    """
    method = LCOR.strip().lower()

    if method == 'турб. режим':
        return Ld_turb(d_mm, Lk)
    elif method == 'cтандартная зависимость':
        return Ld_st(Qgas, d_mm, Mu, Ro, Lk)
    elif method == 'табличные данные':
        return Ld_tab(Ld_tab_value)
    else:
        raise ValueError(f"Unknown method calculete Ld: '{LCOR}'")
