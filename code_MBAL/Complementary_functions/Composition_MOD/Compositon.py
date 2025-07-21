from OGR_calc import OGR_calc

def Composition(P, Pnk, OGR_Method, DataRange, i):
    """
    Расчёт доли i-го компонента по зависимости от КГФ.

    Параметры:
    - P (float): текущее давление, МПа
    - Pnk (float): давление начала конденсации, МПа
    - OGR_Method (str): метод расчёта КГФ
    - DataRange (list of list): исходная таблица состава при Pnk
    - i (int): индекс компонента (1-based)

    Возвращает:
    - доля компонента (float), %
    """
    Z0 = [row[i - 1] for row in DataRange]  # состав при Pnk
    Comp_i = Z0[-1]
    Z_ratios = [1.0 for _ in Z0]  # заглушка — реализация требует данных КГФ

    ogr = OGR_calc(OGR_Method, P)
    ogr0 = OGR_calc(OGR_Method, Pnk)

    numerator = Z_ratios[i - 1] * Comp_i
    denominator = sum(zr * row[i - 1] for zr, row in zip(Z_ratios, DataRange))

    return numerator / denominator * (100 - DataRange[-1][11])
