from .Z_BB import Z_BB
from .Z_GUR import Z_GUR
from .Z_tab import Z_tab
from .Z_PR import Z_PR

def Z_calc(Metod, P_MPA, T_C, Pkri_MPa, Tkri_K, pressure_data=None, z_data=None):
    """
    Универсальная оболочка расчёта коэффициента Z.

    Параметры:
    - Metod (str): метод расчёта ('Beggs  Brill', 'GUR', 'PR', 'таблица')
    - P_MPA (float): давление, МПа
    - T_C (float): температура, °C
    - Pkri_MPa (float): критическое давление, МПа
    - Tkri_K (float): критическая температура, K
    - pressure_data, z_data: табличные данные (для метода 'таблица')

    Возвращает:
    - Z (float): коэффициент сверхсжимаемости
    """
    metod = Metod.strip().lower()

    if metod == 'beggs и brill':
        return Z_BB(P_MPA, T_C, Pkri_MPa, Tkri_K)
    elif metod == 'латонов-гуревич':
        return Z_GUR(P_MPA, T_C, Pkri_MPa, Tkri_K)
    elif metod == 'таблица':
        if pressure_data is None or z_data is None:
            raise ValueError("Не переданы табличные данные для Z_tab")
        return Z_tab(P_MPA, pressure_data, z_data)
    elif metod == 'пенг-робинсон':
        return Z_PR(P_MPA, T_C, XiRange, Pc, Tc, Vc, w)
    else:
        raise ValueError(f"Неизвестный метод расчёта Z: '{Metod}'")
