def Number(Q, DataRange):
    """
    Определение номера интервала, в который попадает значение Q.

    Параметры:
    - Q (float): проверяемое значение
    - DataRange (list): список границ интервалов

    Возвращает:
    - i (int): номер интервала (начиная с 1)
    """
    if Q == 0:
        return 0

    i = 0
    for val in DataRange:
        if val is None:
            break
        if Q < val:
            break
        i += 1

    return i + 1
