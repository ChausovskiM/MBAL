def Aij_PR(P, T, i, j, Pc, Tc, w, Vc=None, kij_matrix=None):
    """
    Расчёт коэффициента Aij для уравнения состояния Пинг–Робинсона.

    Параметры:
    - P, T: давление (Па) и температура (K)
    - i, j: индексы компонентов
    - Pc, Tc: критические давления и температуры (в МПа и K)
    - w: список ацентрических факторов
    - Vc: список критических объёмов (не используется здесь)
    - kij_matrix: матрица коэффициентов бинарного взаимодействия (по умолчанию 0)

    Возвращает:
    - Aij (float)
    """

    def Ai_PR(P, T, idx):
        Pci = Pc[idx] * 1e6  # МПа → Па
        Tci = Tc[idx]
        Tr = T / Tci
        wi = w[idx]
        k = 0.37464 + 1.54226 * wi - 0.26992 * wi**2
        alpha = (1 + k * (1 - Tr**0.5))**2
        return 0.45724 * (Pci / Tci**2) * alpha * (P / T**2)

    kij = kij_matrix[i][j] if kij_matrix else 0.0

    Ai = Ai_PR(P, T, i)
    Aj = Ai_PR(P, T, j)

    return (1 - kij) * (Ai * Aj)**0.5
