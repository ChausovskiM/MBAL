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
#
from code_MBAL.Complementary_functions.Composition_MOD.Composition import Composition

# Функция-обертка для применения к строкам


def main():
    # ==== Зависимость по экспериментальным данным =====
    # Загрузка данных
    with open(r"code_sheets\PVT\gas_components.json", encoding="utf-8") as f:
        gas_components = pd.DataFrame(json.load(f))

    with open(r"code_sheets\Components\composition_input.json", encoding="utf-8") as f:
        data = json.load(f)
    ogr_method = data["method"]
    #
    #print(gas_components)
    # Определяем путь к файлу в зависимости от метода
    if ogr_method == 'experimental data':
        kgf_file = r"code_sheets\KGF\kgf_experimental_input.json"
    elif ogr_method == 'typical dependence':
        kgf_file = r"code_sheets\KGF\kgf_typical_input.json"
    else:
        raise ValueError(f"Unknown method OGR: {ogr_method}")
    # открываем нужный файл
    with open(kgf_file, encoding="utf-8") as f:
            data = json.load(f)
    P_nk = data['Pnk']



    #print(P_nk)
    #
    # ==== Зависимость состава от давления (расчет от кривой КГФ), % ====
    df_components = pd.DataFrame(columns=["P_Mpa","N2","CO2","H2S","H2","H2O","He","CH4","C2H6","C3H8","i-C4H10","n-C4H10","C5+"])
    df_components['P_Mpa'] = np.linspace(0.1, P_nk, 30)
    # Расчет для каждого давления и компонента
    components_order = ["N2","CO2","H2S","H2","H2O","He","CH4","C2H6","C3H8","i-C4H10","n-C4H10","C5+"] # 0-11
    
    for i,component in enumerate(components_order):
        df_components[component] = df_components['P_Mpa'].apply(
            lambda P: Composition(
                P_MPA=P,
                Pnk_MPA=P_nk,
                ogr_method=ogr_method,
                mol_fractions = gas_components['mol_fraction_pct'],
                component_idx=i  # 0-11
            )
        )
    
    # Сохранение результатов
    df_components.to_json('code_sheets/Components/components_output.json', orient='records', lines=True)
    # Создаем фигуру и оси для графиков
    fig, axs = plt.subplots(4, 3, figsize=(18, 12))

    # Построение графиков для каждого столбца
    for i, column in enumerate(components_order):
        row = i // 3
        col = i % 3
        axs[row, col].plot(df_components['P_Mpa'], df_components[column], label=column)
        axs[row, col].set_xlabel('P_Mpa')
        axs[row, col].set_ylabel('Мольная доля компонента, %')
        axs[row, col].legend()
        axs[row, col].grid(True)

    fig.savefig('code_sheets/Components/components_graph.png', dpi=300, bbox_inches='tight')


if __name__ == "__main__":
    main()