from code_MBAL.Density_MOD.Density import Density
from code_MBAL.Density_MOD.Density_tab import Density_tab

def Density_calc(Metod, P_MPA, T_C, Z, pressure_data=None, rho_data=None):
    """
    Универсальная оболочка расчёта плотности газа.

    Параметры:
    - Metod (str): метод расчёта ('аналитический', 'таблица')
    - P_MPA (float): давление, МПа
    - T_C (float): температура, °C
    - Z (float): коэффициент сверхсжимаемости
    - m (float): относительная молекулярная масса (по воздуху)
    - pressure_data, rho_data: табличные данные (если метод табличный)

    Возвращает:
    - ρ (float): плотность газа, кг/м³
    """
    metod = Metod.strip().lower()

    if P_MPA == 0:
        return 0.0

    if metod == 'корреляция':
        return Density(P_MPA, T_C, Z)
    elif metod == 'таблица':
        if pressure_data is None or rho_data is None:
            raise ValueError("Не переданы табличные данные для Density_tab")
        return Density_tab(P_MPA, pressure_data, rho_data)
    else:
        raise ValueError(f"Unknown method calculete density: '{Metod}'")
