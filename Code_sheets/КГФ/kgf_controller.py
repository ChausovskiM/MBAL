import openpyxl
import os
import json
import math
import sys
#
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
#

# Добавляем корень проекта в пути Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)
#print(sys.path)
#
from code_MBAL.Complementary_functions.OGR import OGR
from code_MBAL.Complementary_functions.OGR_type import OGR_TYPE
from code_MBAL.Complementary_functions.KIK import KIK
#
# Загрузка данных
#
#print(sys.path)
#print(os.getcwd())

def model_experimental(P, A, B, C, D, E):
   return A * P**4 + B * P**3 + C * P**2 + D * P + E

def model_type(P, A, B, C, D, E, F, G):
   return A * P**6 + B * P**5 + C * P**4 + D * P**3 + E * P**2 + F* P + G


def main():
    # ==== Зависимость по экспериментальным данным =====
    # Загрузка данных
    with open(r"code_sheets\KGF\kgf_experimental_input.json", encoding="utf-8") as f:
        data = json.load(f)
    # Извлекаем отдельные переменные
    P_pl = data["Ppl"]
    P_nk = data["Pnk"]
    # Создаем DataFrame из points
    kgf_experimental = pd.DataFrame(data["points"])

    # Подгонка параметров
    #model = np.polyval([0,0,0,0,0],kgf_experimental["P"].values)
    params, covariance = curve_fit(model_experimental, kgf_experimental["P"].values, kgf_experimental["KGF_fact"].values)

    A, B, C, D, E = params # найденные коэффициенты аппрксимации экспер кривой КГФ
    #
    # добавляем сотлбцы аппроксимации и ошибки(mape,%)
    kgf_experimental['KGF_approximate'] = model_experimental(kgf_experimental['P'], A, B, C, D, E)
    kgf_experimental['KGF_mape'] = 100 * (kgf_experimental['KGF_approximate'] - kgf_experimental['KGF_fact']) / kgf_experimental['KGF_fact']
    #
    C5_plus = OGR(P_pl,P_nk,[A, B, C, D, E])
    kik = KIK(P_pl,P_nk,[A, B, C, D, E])
    #
    #
    # ==== Типовая зависимость ===== 
    with open(r"code_sheets\KGF\kgf_typical_input.json", encoding="utf-8") as f:
        data = json.load(f)

    kgf_type = data['KGF']
    P_nk_type = data["Pnk"]
    kik_type = data["KIK"]
    df_type = OGR_TYPE(P_nk_type,kgf_type,kik_type)

    params, covariance = curve_fit(model_type,df_type["P"].values,df_type["KGF"].values)
    A_type, B_type, C_type, D_type, E_type, F_type, G_type = params
    # ==============================
    #  
    # ==== Сводная таблица зависимости КГФ от давления для расчета ====
    df_svod = pd.DataFrame({"P":np.linspace(0.1, P_nk, 30)}) # ПОСЛЕДННЯ ТОЧКА ДАВЛЕНИЕ НАЧАЛА КОНДЕКНСАЦИИ
    df_svod['KGF_experiment'] = model_experimental(df_svod['P'], A, B, C, D, E)
    df_svod['KGF_type'] = model_type(df_svod['P'], A_type, B_type, C_type, D_type, E_type, F_type, G_type)
    # =================================================================
    #
    print(f"{C5_plus:.3f},{kik:.3f}")   
    print(f"A = {A:.7f}, B = {B:.7f}, C = {C:.7f}, D = {D:.7f}, E = {E:.7f}",P_pl)

    summary = {
        "coeff_experiment":[A, B, C, D, E],
        "C5_plus":C5_plus,
        "kik":kik,
        #
        "coef_type": [A_type, B_type, C_type, D_type, E_type, F_type, G_type],

        "results_table": df_svod.to_dict(orient="list") 
    }

    with open('code_sheets/KGF/kgf_outputs.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=4)
    # P_fit = np.linspace(min(kgf_experimental["P"].values), max(kgf_experimental["P"].values), 100)
    # KGF_fit = model_experimental(P_fit, A, B, C, D, E)

    # plt.scatter(kgf_experimental["P"], kgf_experimental["KGF_fact"], label="Исходные данные", color="red")
    # plt.plot(P_fit, KGF_fit, label="Аппроксимация", color="blue")
    # plt.plot(df_type['P'], df_type['KGF'], label="type", color="green")
    # plt.xlabel("P")
    # plt.ylabel("KGF_fact")
    # plt.legend()
    # plt.grid()
    # plt.show()

    #

    plt.plot(df_svod['P'], df_svod["KGF_experiment"], label="experimental", color="blue")
    plt.plot(df_svod['P'], df_svod['KGF_type'], label="type", color="green")
    plt.xlabel("P")
    plt.ylabel("KGF")
    plt.legend()
    plt.grid()
    plt.show()


if __name__ == "__main__":
    main()