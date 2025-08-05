from Composition import Composition
from Composition_tab import Composition_tab

def Composition_calc(P_MPA, Pnk_MPA, Ogr_Metod, Comp_DataRange, index, Metod):
    """
    Выбор метода расчёта компонентного состава газа.

    Параметры:
    - P_MPA (float): текущее давление, МПа
    - Pnk_MPA (float): давление начала конденсации, МПа
    - Ogr_Metod (str): метод расчёта ОГР
    - Comp_DataRange (list of list): таблица компонентного состава
    - index (int): индекс компонента (1-based)
    - Metod (str): выбранный метод ('На основе КГФ', 'Табличные данные', 'отключено')

    Возвращает:
    - доля компонента (float), %
    """
    method = Metod.strip().lower()

    if method == 'на основе кгф':
        return Composition(P_MPA, Pnk_MPA, Ogr_Metod, Comp_DataRange, index)
    elif method == 'табличные данные':
        return Composition_tab(P_MPA, index, Comp_DataRange)
    elif method == 'отключено':
        return 0.0
    else:
        raise ValueError(f"Неизвестный метод расчёта состава: '{Metod}'")
