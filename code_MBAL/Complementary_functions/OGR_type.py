from code_MBAL.Complementary_functions.KIK import KIK

import numpy as np
import pandas as pd

def OGR_TYPE(P: float, C5: float, KIK: float) -> pd.DataFrame:
    """
    Аналог VBA-функции OGR_TYPE, возвращающий DataFrame с колонками ["Давление", "КГФ"].
    
    Parameters:
        P (float): Максимальное давление (атм)
        C5 (float): Содержание C5+ (г/м³)
        KIK (float): Коэффициент извлечения конденсата (0.2 ≤ KIK ≤ 1)
        
    Returns:
        pd.DataFrame: Давление и соответствующий КГФ
    """
    # Ограничение KIK снизу
    KIK = max(KIK, 0.2)
    
    # Давления: 0%, 10%, ..., 100% от P
    pressures = np.linspace(0, P, 11)
    
    # Расчёт A1 и B1
    if KIK <= 0.454522645:
        A1 = 0
        B1 = 2.6884 * KIK - 1.2219
    else:
        A1 = 1.8328 * KIK - 0.8331
        B1 = 0
    
    # Расчёт КГФ для каждой точки
    kgf_values = np.zeros(11)
    kgf_values[0] = C5 * 0.25 + 0.75 * C5 * A1
    kgf_values[1] = C5 * 0.1 + 0.9 * C5 * A1
    kgf_values[2] = C5 * 0.05 + 0.95 * C5 * A1
    kgf_values[3] = C5 * 0.04 + 0.96 * C5 * A1
    kgf_values[4] = C5 * 0.2 + 0.8 * C5 * A1 + 0.21 * C5 * B1
    kgf_values[5] = C5 * 0.35 + 0.65 * C5 * A1 + 0.4 * C5 * B1
    kgf_values[6] = C5 * 0.55 + 0.45 * C5 * A1 + 0.64 * C5 * B1
    kgf_values[7] = C5 * 0.75 + 0.25 * C5 * A1 + 0.85 * C5 * B1
    kgf_values[8] = C5 * 0.9 + 0.1 * C5 * A1 + 0.9 * C5 * B1
    kgf_values[9] = C5 * 0.97 + 0.03 * C5 * A1 + 0.6 * C5 * B1
    kgf_values[10] = C5  # При 100% давления КГФ = C5
    
    # Сбор в DataFrame
    df = pd.DataFrame({
        "P": pressures,
        "KGF": kgf_values
    })
    
    return df