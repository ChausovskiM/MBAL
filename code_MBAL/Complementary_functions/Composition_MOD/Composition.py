import pandas as pd
import numpy as np

from code_MBAL.Complementary_functions.OGR_calc import OGR_calc

def Composition(P_MPA: float, 
               Pnk_MPA: float, 
               ogr_method: str, 
               mol_fractions: list, 
               component_idx: int) -> float:
    """
    Расчет состава газовой смеси для конкретного компонента.
    
    Parameters:
        P_MPA: Давление (МПа)
        Pnk_MPA: Давление начала конденсации (МПа)
        ogr_method: Метод расчета КГФ
        mol_fractions: Список мольных долей [N2, CO2, ..., C5+] (12 элементов)
        component_idx: Индекс компонента (0-11)
    
    Returns:
        Расчетное значение компонента
    """
    # Порядок компонентов (как в VBA)
    components_order = ["N2","CO2","H2S","H2","H2O","He","C1","C2H6","C3H8","i-C4H10","n-C4H10","C5+"]
    
    # 1. Расчет OGR
    OGRi = OGR_calc(ogr_method, P_MPA)
    OGRnk = OGR_calc(ogr_method, Pnk_MPA)
    # OGRi,OGRnk =10,12
    nZ12 = OGRi / OGRnk if OGRnk != 0 else 0
    
    # 2. Нормированное давление
    Pn = 1 if P_MPA > Pnk_MPA else P_MPA / Pnk_MPA
    
    # 3. Полиномиальные коэффициенты (как в VBA)
    poly_coeffs = {
        0: [1.16866, -3.80104, 4.70441, -2.66594, 0.58786, 0.03468],    # N2
        1: [5.67824, -18.35399, 22.50612, -12.56254, 2.68089, 0.19084],  # CO2
        6: [591.70043, -1919.30535, 2365.62924, -1331.36631, 289.24039, 18.59416],  # C1
        7: [52.10356, -168.12239, 205.54267, -114.04218, 23.86944, 1.99061],       # C2H6
        8: [18.9892, -61.23216, 74.64346, -40.99494, 8.17008, 0.99644],            # C3H8
        9: [6.99511, -21.32264, 24.26467, -12.19911, 2.07018, 0.36287],           # i-C4H10
        10: [3.68772, -11.94632, 14.60604, -7.97511, 1.48721, 0.28334]            # n-C4H10
    }
    
    # 4. Расчет Z и Z0
    if component_idx in poly_coeffs:
        coeffs = poly_coeffs[component_idx]
        Z = sum(c * (Pn**(5-j)) for j, c in enumerate(coeffs)) * nZ12
        Z0 = sum(coeffs)
    elif component_idx in [2, 3, 4, 5]:  # H2S, H2, H2O, He
        Z = mol_fractions[component_idx] * nZ12
        Z0 = mol_fractions[component_idx]
    elif component_idx == 11:  # C5+
        Z = nZ12
        Z0 = 1
    
    # 5. Расчет суммы для знаменателя
    sum_terms = 0
    for idx in range(11):  # 0-10 (без C5+)
        if idx in poly_coeffs:
            coeffs = poly_coeffs[idx]
            Z_comp = sum(c * (Pn**(5-j)) for j, c in enumerate(coeffs)) * nZ12
            Z0_comp = sum(coeffs)
        else:
            Z_comp = mol_fractions[idx] * nZ12
            Z0_comp = mol_fractions[idx]
        
        if Z0_comp > 0:
            sum_terms += (Z_comp / Z0_comp) * mol_fractions[idx]
    
    # 6. Итоговый расчет
    if sum_terms == 0:
        return mol_fractions[component_idx]
    
    if component_idx == 11:  # C5+
        return nZ12 * mol_fractions[11]
    elif Z0 > 0:
        return (Z / Z0) * mol_fractions[component_idx] / sum_terms * (100 - nZ12 * mol_fractions[11])
    else:
        return 0.0
    
