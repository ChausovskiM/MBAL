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
    P_nk_exp = data["Pnk"]
    # Создаем DataFrame из points
    kgf_experimental = pd.DataFrame(data["kgf_exp_table"])

    # Подгонка параметров
    #model = np.polyval([0,0,0,0,0],kgf_experimental["P"].values)
    params_exp = curve_fit(model_experimental, kgf_experimental["P"].values, kgf_experimental["KGF_fact"].values)[0]

    A, B, C, D, E = params_exp # найденные коэффициенты аппрксимации экспер кривой КГФ
    #
    # добавляем сотлбцы аппроксимации и ошибки(mape,%)
    kgf_experimental['KGF_approximate'] = model_experimental(kgf_experimental['P'], A, B, C, D, E)
    kgf_experimental['KGF_mape'] = 100 * (kgf_experimental['KGF_approximate'] - kgf_experimental['KGF_fact']) / kgf_experimental['KGF_fact']
    #
    C5_plus = OGR(P_pl,P_nk_exp,params_exp)
    kik = KIK(P_pl,P_nk_exp,params_exp)
    #
    #
    # ==== Типовая зависимость ===== 
    with open(r"code_sheets\KGF\kgf_typical_input.json", encoding="utf-8") as f:
        data = json.load(f)
    # ==============================
    kgf_type = data['KGF']
    P_nk_type = data["Pnk"]
    kik_type = data["KIK"]
    df_type = OGR_TYPE(P_nk_type,kgf_type,kik_type)

    params_type = curve_fit(model_type,df_type["P"].values,df_type["KGF"].values)[0] #коэффициенты аппроксимации
    # ==============================
    #  
    # ==== Сводная таблица зависимости КГФ от давления для расчета ====
    df_svod = pd.DataFrame({"P":np.linspace(0.1,max(P_nk_exp,P_nk_type)*1.1, 30)}) # ПОСЛЕДННЯ ТОЧКА ДАВЛЕНИЕ НАЧАЛА КОНДЕКНСАЦИИ
    df_svod['KGF_experiment'] = df_svod['P'].apply(lambda P: np.polyval(params_exp,P) if P<=P_nk_exp else C5_plus)
    #
    df_svod['KGF_type'] = df_svod['P'].apply(lambda P: np.polyval(params_type,P) if P<=P_nk_type else kgf_type)
    # =================================================================
    #
    summary = {
        "C5_plus":C5_plus,
        "kik":kik,
        "coeff_experiment":[A, B, C, D, E],
        #
        "coef_type": list(params_type),

        "results_table": df_svod.round(5).to_dict(orient="list") 
    }
    #
    with open('code_sheets/KGF/kgf_output.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=4)
    #
    # Создаем фигуру с 3 подграфиками (1 строка, 3 столбца)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5))

    # --- График 1: Экспериментальная зависимость ---
    ax1.scatter(kgf_experimental["P"], kgf_experimental["KGF_fact"], label="Экспериментальная", color="gold")
    ax1.plot(kgf_experimental['P'], kgf_experimental["KGF_approximate"], label="Экспериментальная аппроксимация", color="black")
    ax1.set_title("Аппроксимация экспериментальной зависимости")
    ax1.set_xlabel("P")
    ax1.set_ylabel("KGF")
    ax1.legend()
    ax1.grid()

    # --- График 2: Типовая зависимость ---
    ax2.plot(df_svod['P'], df_svod['KGF_type'], label="Типовая", color="green", marker='s')
    ax2.set_title("Аппроксимация типовой зависимости")
    ax2.set_xlabel("P")
    ax2.set_ylabel("KGF")
    ax2.legend()
    ax2.grid()
    # --- График 3: Совмещенный ---
    ax3.plot(df_svod['P'], df_svod["KGF_experiment"], label="Экспериментальная", color="blue", marker='o')
    ax3.plot(df_svod['P'], df_svod['KGF_type'], label="Типовая", color="green", marker='s')
    ax3.set_title("Сравнение зависимостей")
    ax3.set_xlabel("P")
    ax3.set_ylabel("KGF")
    ax3.legend()
    ax3.grid()

    fig.savefig('code_sheets/KGF/kgf_graph.png', dpi=300)


if __name__ == "__main__":
    main()