import numpy as np
import pandas as pd
import json

# from OGR_exp import OGR_exp
# from OGR_zav import OGR_zav
#from OGR_tab1 import OGR_tab1

def OGR_calc(Metod, P_MPA):
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
    
    with open(r"code_sheets\KGF\kgf_output.json", encoding="utf-8") as f:
        kgf_outputs = pd.DataFrame(json.load(f)['results_table'])


    metod = Metod.strip()
    if metod == "experimental data": 
        return np.interp(P_MPA,kgf_outputs['P'],kgf_outputs['KGF_experiment'])
    elif metod == "typical dependence":
        return np.interp(P_MPA,kgf_outputs['P'],kgf_outputs['KGF_type'])
    elif metod == "table data":
        return  0 #OGR_tab1(P_MPA)
    elif metod == "gas field":
        return 0.0
    else:
        raise ValueError(f"Unknown method calculated KGF: '{Metod}'")
    