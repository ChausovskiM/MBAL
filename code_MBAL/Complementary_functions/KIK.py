def KIK(P, Pnk, DataRange):
    """
    Расчёт коэффициента извлечения конденсата (KIK).

    Параметры:
    - P (float): текущее давление, МПа
    - Pnk (float): давление начала конденсации, МПа
    - DataRange (list): коэффициенты полинома ОГР (по убыванию степени)

    Возвращает:
    - KIK (float): коэффициент извлечения газа (0..1)
    """
    n = len(DataRange)

    # OGR при Pnk
    OGRnk = sum(DataRange[i] * Pnk ** (n - i - 1) for i in range(n))

    # Площадь под полиномом от Pnk до 1.01325 (Sdown)
    Sdown = sum(
        DataRange[i] * (Pnk ** (n - i) - 1.01325 ** (n - i)) / (n - i)
        for i in range(n)
    )

    # Прямоугольник выше Pnk (Supnk)
    Supnk = (P - Pnk) * OGRnk

    # Общая площадь под полиномом (Stotal)
    Stotal = (P - 1.01325) * OGRnk

    return (Sdown + Supnk) / Stotal if Stotal != 0 else 0.0
