import numpy as np
import pandas as pd
import json

from code_MBAL.Complementary_functions.OGR_tab1 import OGR_tab1

# from OGR_exp import OGR_exp
# from OGR_zav import OGR_zav
#from OGR_tab1 import OGR_tab1

def OGR_calc(Metod, P_MPA, pressure_data=None, ogr_data=None):
    """
    Выбор методики расчета КГФ (конденсатогазового фактора)
    
    Parameters:
        Metod: Метод расчета ("Экспер. данные", "Типовая зависимость", "Табличные данные", "Газовое месторождение")
        P_MPA: Давление в МПа
        
    Returns:
        Значение КГФ в г/м3
    """
    if P_MPA == 0:
        return 0.0
    
    metod = Metod.strip()
    if metod in {"experimental data", "typical dependence"}:
        with open(r"code_sheets\KGF\kgf_output.json", encoding="utf-8") as f:
            kgf_outputs = pd.DataFrame(json.load(f)['results_table'])

    if metod == "experimental data":
        return np.interp(P_MPA,kgf_outputs['P'],kgf_outputs['KGF_experiment'])
    elif metod == "typical dependence":
        return np.interp(P_MPA,kgf_outputs['P'],kgf_outputs['KGF_type'])
    elif metod == "table data":
        if pressure_data is None or ogr_data is None:
            raise ValueError("Не переданы pressure_data и ogr_data для табличного КГФ")
        return OGR_tab1(P_MPA, pressure_data, ogr_data)
    elif metod == "gas field":
        return 0.0
    else:
        raise ValueError(f"Unknown method calculated KGF: '{Metod}'")
