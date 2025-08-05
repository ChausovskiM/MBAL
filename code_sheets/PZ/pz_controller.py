import openpyxl
import os
import json
import math
import sys
#
from datetime import datetime
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
#
from code_MBAL.Z_MOD.Z_calc import Z_calc
from code_MBAL.MBAL_fP_MOD.MBAL_fP import MBAL_fP
from code_MBAL.MBAL_fP_MOD.MBAL_Hurst import Mbal_Hurst
#from code_MBAL.MBAL_fP_MOD.MBAL_fP import Z_calc

def calc_mixture_params(gas_components):
    """
    Вычисляет средние параметры смеси: молекулярный вес, критическую температуру и давление.

    Ожидается, что mol_fraction_pct передаётся в процентах (%).
    """
    Mw_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Mw"] for comp in gas_components)
    Tc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Tc"] for comp in gas_components)
    Pc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Pc"] for comp in gas_components)

    return Mw_mix, Tc_mix, Pc_mix

def main():
# загрузка исходных данных
    with open(r"code_sheets\PZ\pz_input.json", 'r', encoding='utf-8') as f:
        pz_input = json.load(f)

    oiz_gas = pz_input['nbz_gas'] - pz_input['Cum_gas_under_pred']
    nbz_cond = pz_input['nbz_gas']*88.2/1000
    Z_method = pz_input["Z_method"]
    #
    # # открываем саму таблицу
    df_dev = pd.DataFrame(pz_input['dev_table'])
    
    Z_calculate = Z_calc(Z_method,pz_input['P_reservor_init'],pz_input['T_reservor_init'])
    df_dev['Z'] =  df_dev['P'].apply(lambda P: Z_calc(Z_method,P, pz_input['T_reservor_init']))

    # расчет объемника
    Bg = 101325 * (pz_input['T_reservor_init'] + 273.15) * Z_calculate / (pz_input['P_reservor_init']*10**6 * 293.15) #вместио функции Bg
    #объем залежи
    plast_value = pz_input['nbz_gas'] * Bg
    plast_area = plast_value / pz_input['gnt'] # дилм на ГНТ [м]
    #
    # расчет оставшихся колонок таблицы
    df_dev['P/Z'] = df_dev['P'] / df_dev['Z']
    # 18 params почему 21 параметр надо
    df_dev['P_calc'] = df_dev.apply(lambda row: MBAL_fP(pz_input['P_reservor_init'], 
                                                        pz_input['T_reservor_init'], 
                                                        Z_calculate, 
                                                        pz_input['nbz_gas'], 
                                                        row['Cum_Gas'], 
                                                        pz_input['pore_comp'], 
                                                        pz_input['water_comp'], 
                                                        pz_input["aquifer_permeability"], 
                                                        pz_input["aquifer_porosity"], 
                                                        pz_input["aquifer_radius"], #B24 
                                                        pz_input["aquifer_thickness"], #B22 
                                            (datetime.strptime(row['date'], '%Y-%m-%d') - datetime.strptime(pz_input["start_dev_date"], '%Y-%m-%d')).days, 
                                                        pz_input["drainage_angle"], 
                                                        pz_input["water_viscosity"], 
                                                        pz_input["sw"],
                                                        Z_method, 
                                                        ),axis=1)
    #
    df_dev['Z_calc'] = df_dev['P_calc'].apply(lambda P: Z_calc(Z_method,P,pz_input['T_reservor_init']))
    df_dev['P_calc/Z_calc'] = df_dev['P_calc'] / df_dev['Z_calc']
    # вопрос в дате???
    df_dev['Wi'] = df_dev.apply(lambda row: Mbal_Hurst(pz_input['pore_comp']/1000,
                                                       pz_input['water_comp']/1000,
                                                       pz_input['P_reservor_init'], 
                                                       row['P_calc'],
                                                       pz_input["aquifer_permeability"],
                                            (datetime.strptime(row['date'], '%Y-%m-%d') - datetime.strptime(pz_input["start_dev_date"], '%Y-%m-%d')).days, 
                                                       pz_input["aquifer_porosity"],
                                                       pz_input["water_viscosity"],
                                                       pz_input["aquifer_radius"], #B24
                                                       pz_input["aquifer_thickness"], #B22
                                                       pz_input["drainage_angle"], 
                                                       ),axis=1)
    
    df_dev['zapolnenie, %'] = 100*df_dev['Wi'] / plast_value
    df_dev['H lift'] = df_dev['Wi'] / plast_area #???

    summary = {
        "oiz_gas":round(oiz_gas,4),
        "nbz_cond":round(nbz_cond,4),
        #
        #"Bg": Bg,
        "Z_calc":round(Z_calculate,4),
        "plast_value":round(plast_value,4),
        "plast_area":round(plast_area,4),
        "results_table": df_dev.to_dict(orient="list") 
    }

    with open('code_sheets/PZ/pz_outputs.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=4)
    #print(df_dev)
    # Создаем фигуру с двумя подграфиками
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    # Первый график: P/Z vs Накопленный отбор

    ax1.scatter(df_dev['Cum_Gas'], df_dev['P/Z'], label='факт', marker='o',color= 'orange')
    ax1.scatter(df_dev['Cum_Gas'], df_dev['P_calc/Z_calc'],  label='расчет', marker='D',color= 'blue')
    ax1.set_xlabel('Накопленный отбор, млн.м³')
    ax1.set_ylabel('P/Z, МПа')
    ax1.set_ylim(bottom=0,top = max(df_dev['P/Z'].max(), df_dev['P_calc/Z_calc'].max()) * 1.3)  # Ось Y начинается с 0
    ax1.legend()
    ax1.grid(True)

    # Второй график: Отбор vs Накопленный отбор
    ax2.scatter(df_dev['Cum_Gas'], df_dev['P'], label='факт', marker='o',color= 'orange')
    ax2.scatter(df_dev['Cum_Gas'], df_dev['P_calc'], label='расчет', marker='D',color= 'blue')
    ax2.set_xlabel('Накопленный отбор, млн.м³')
    ax2.set_ylabel('P, МПа')
    ax2.set_ylim(bottom=0, top = max(df_dev['P'].max(), df_dev['P_calc'].max()) * 1.3)  # Ось Y начинается с 0
    ax2.legend()
    ax2.grid(True)

    # Настройка общего заголовка и отступов
    plt.tight_layout()

    # Отображение графиков
    plt.show()
if __name__ == "__main__":
    main()