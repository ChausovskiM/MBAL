import openpyxl
import os
import json
import math
import sys
#
import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt
#
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from code_MBAL.Z_MOD.Z_calc import Z_calc
from code_MBAL.Z_MOD.Z_PR import Z_PR
from code_MBAL.Z_MOD.Z_GUR import Z_GUR
from code_MBAL.Z_MOD.Z_BB import Z_BB
from code_MBAL.Density_MOD.Density_calc import Density_calc
from code_MBAL.Visc_MOD.Visc_calc import Visc_calc
from code_MBAL.Visc_MOD.Visc_Lee_Gonzalez import Visc_Lee_Gonzalez
from code_MBAL.Visc_MOD.Visc_JST import Visc_JST
# print(os.getcwd())
# === Загрузка данных ===
# def load_input(path):r
#     with open(path, "r", encoding="utf-8") as f:
#         return json.load(f)

# def load_components(path):
#     with open(path, "r", encoding="utf-8") as f:
#         return json.load(f)

# === Главный расчётный блок ===
def calc_mixture_params(gas_components):
    """
    Вычисляет средние параметры смеси: молекулярный вес, критическую температуру и давление.

    Ожидается, что mol_fraction_pct передаётся в процентах (%).
    """
    Mw_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Mw"] for comp in gas_components)
    Tc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Tc"] for comp in gas_components)
    Pc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Pc"] for comp in gas_components)

    return Mw_mix, Tc_mix, Pc_mix

def prepare_inputs_from_components(gas_components):
    """
    Преобразует список компонентов газа в набор входных параметров
    для функции Z_PR: XiRange, Pc, Tc, Vc, w

    Параметры:
    - gas_components (list[dict]): список словарей с параметрами компонентов

    Возвращает:
    - XiRange, Pc, Tc, Vc, w (все списки float)
    """
    gas_components = pd.DataFrame(gas_components)

    XiRange = gas_components['mol_fraction_pct']
    MwRange = gas_components['Mw']
    TcRange = gas_components['Tc']
    PcRange = gas_components['Pc']
    VcRange = gas_components['Vc']
    ZcRange = gas_components['Zc']
    wRange = gas_components['w']

    # XiRange = gas_components['mol_fraction_pct']
    # Pc = gas_components['Pc']  # МПа
    # Tc = gas_components['Tc']  #К  
    # Vc = gas_components['Vc']  # см3/моль  
    # w  = gas_components['w']   #безразмерный 

    return XiRange,MwRange,TcRange,PcRange,VcRange,ZcRange,wRange # Pc, Tc, Vc, w


#os.chdir(os.path.dirname(os.path.abspath(__file__)))
# === Расчёт значений для таблицы (строки 4,5,6,8,10,12,13,15,17,18,19) ===
def main():
    
    # Получаем путь к директории скрипта
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # file_path = os.path.join(script_dir, "import_properties.json")
    #
    with open(r"code_sheets\PVT\input_properties.json", 'r', encoding='utf-8') as f:
        props = json.load(f)

    #file_path = os.path.join(script_dir, "gas_components.json")
    #
    with open(r"code_sheets\PVT\gas_components.json", 'r', encoding='utf-8') as f:
        gas_components = json.load(f)
    # props = load_input("input_properties.json")
    # gas_components = pd.DataFrame(load_components("gas_components.json"))
    

    Mw_mix, Tc_mix, Pc_mix = calc_mixture_params(gas_components)
    #XiRange, Pc, Tc, Vc, w = prepare_inputs_from_components(gas_components)
    XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange,wRange = prepare_inputs_from_components(gas_components)
    # распаковка словаря начальных свойств
    P_Mpa = props["P_plast_MPA"]
    T_C_plast = props["T_plast_C"]
    
    Z_method = props["Z_method"].strip().lower()
    # density_method = props["density_method"]
    viscosity_method = props["viscosity_method"].strip().lower()
    Z_fact = props["Z_fact"] #строка 8
    
    # Расчёт таблицы расчётных параметров (строки 4,5,6,8,10,12,13,15,17,18,19)
    Ppr = P_Mpa / Pc_mix #строка 4
    Tpr = (T_C_plast + 273.15) / Tc_mix #строка 5

    m = Mw_mix / 28.96 #строка 6

    #=== строка 8
    Z_calculate = Z_calc(Z_method, P_Mpa, T_C_plast)
    #===
    deviation_Z = (Z_calculate-Z_fact)/Z_fact*100 #строка10
    #
    #=== расчет плотности
    rho0 = Mw_mix / 24.04  # нормальная плотность, кг/м³
    rho = rho0 * P_Mpa*10**6 * 293.15 / (101325 * (T_C_plast+273.15) * Z_calculate) #строка 12
    rho_std = rho0 * 0.101325*10**6 * 293.15 / (101325 * (20+273.15) * 1) #строка 12
    #===
    #
    #=== строка 15 def Visc_calc(Metod, P_MPA, T_C, Z, Plot, pressure_data=None, visc_data=None):

    mu = Visc_calc(viscosity_method,P_Mpa, T_C_plast, Z_calculate, rho)
    visc_std = Visc_calc(viscosity_method,0.10325, 20, 1, rho_std)
    #===
    #
    deviation_mu = (mu - props['viscosity_fact_cP'])/props['viscosity_fact_cP']*100 #строка 17
    #
    Bg = 101325 * (T_C_plast + 273.15) * Z_calculate / (P_Mpa*10**6 * 293.15) #строка 19 #функция Bg

    summary = {
        "Ppr": round(Ppr, 4),
        "Tpr": round(Tpr, 4),
        "m": round(m, 4),
        "Z_calc": round(Z_calculate, 5),
        "Z_deviation": round(deviation_Z, 2),
        "rho": round(rho, 3),
        "rho_std": round(rho_std, 3),
        "mu": round(mu, 5),
        "mu_std": round(visc_std, 3),
        "mu_deviation": round(deviation_mu, 2),
        "Bg": round(Bg, 5)
    }

    with open("code_sheets/PVT/output_pvt_summary1.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    #=======ТАБЛИЦА 2.ТАБЛИЧНЫЕ ДАННЫЕ=========
    P_list = [0.1, 5.1, 10.1, 15.1, 20.1, 25.1, 30.1, 35.1, 40.1, 45.1, 50.1, 55.1, 60.1, 65.1, 70.1]
    #P_list = np.linspace(0.1,P_plast*1.3,5000) # Захардкоженный массив давлений (МПа)
    
    # Создаем DataFrame из списка давлений
    df = pd.DataFrame({'P_MPA': P_list})
    
    # Рассчитываем Z-факторы
    #df['ZPr'] = df['P_MPA'].apply(lambda P: Z_PR(P, T_C_plast, XiRange, PcRange, TcRange, VcRange, wRange))
    df['ZPr'] = df['P_MPA'].apply(lambda P: Z_PR(P, T_C_plast, XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange, wRange))
    df['ZBB'] = df['P_MPA'].apply(lambda P: Z_BB(P, T_C_plast, Pc_mix, Tc_mix))
    df['ZGUR'] = df['P_MPA'].apply(lambda P: Z_GUR(P, T_C_plast, Pc_mix, Tc_mix))
    # Рассчитываем плотность
    df['Density'] = rho0 * df['P_MPA']*10**6 * 293.15 / (101325 * (T_C_plast + 273.15) * df['ZBB'])
    # Рассчитываем вязкости
    df['mu_LG'] = df.apply(lambda row: Visc_Lee_Gonzalez(T_C_plast,row['Density'], Mw_mix)/1000, axis=1)
    #df['mu_JST'] = df.apply(lambda row: Visc_JST(row['P_MPA'], T_C_plast, row['ZBB']), axis=1)
    df['mu_JST'] = df.apply(lambda row:  Visc_JST(row['P_MPA'], T_C_plast, row['ZBB'], XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange)/1000, axis=1)
    # Рассчитываем объемный коэффициент
    df['Bg'] = 101325 * (T_C_plast + 273.15) * df['ZBB'] / (df['P_MPA']*10**6 * 293.15)
    df.loc[0,'Bg'] = pd.NA

    df.to_json('code_sheets/PVT/output_pvt_results1.json', orient='records', lines=True)
    df.to_excel('code_sheets/PVT/graf.xlsx')
    # === 2 строки × 2 столбца ===
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))

    # --- Z-фактор ---
    axs[0, 0].plot(df['P_MPA'], df['ZPr'], label="Z_PR", marker='o')
    axs[0, 0].plot(df['P_MPA'], df['ZBB'], label="Z_BB", marker='x')
    axs[0, 0].plot(df['P_MPA'], df['ZGUR'], label="Z_GUR", marker='s')
    axs[0, 0].set_title("Z-фактор по давлению")
    axs[0, 0].set_ylabel("Z")
    axs[0, 0].legend()
    axs[0, 0].grid(True)

    # --- Плотность ---
    axs[0, 1].plot(df['P_MPA'], df['Density'], marker='o', color='tab:blue')
    axs[0, 1].set_title("Плотность газа по давлению")
    axs[0, 1].set_ylabel("ρ, кг/м³")
    axs[0, 1].grid(True)

    # --- Вязкость ---
    axs[1, 0].plot(df['P_MPA'], df['mu_LG'], label="Lee-Gonzalez", marker='o')
    axs[1, 0].plot(df['P_MPA'], df['mu_JST'], label="Jossi-Stiel-Thodos", marker='x')
    axs[1, 0].set_title("Вязкость газа по давлению")
    axs[1, 0].set_xlabel("Давление, МПа")
    axs[1, 0].set_ylabel("μ, сП")
    axs[1, 0].legend()
    axs[1, 0].grid(True)

    # --- Bg ---
    axs[1, 1].plot(df['P_MPA'], df['Bg'], marker='o', color='tab:green')
    axs[1, 1].set_title("Объёмный коэффициент Bg")
    axs[1, 1].set_xlabel("Давление, МПа")
    axs[1, 1].set_ylabel("Bg, м³/м³")
    axs[1, 1].grid(True)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()