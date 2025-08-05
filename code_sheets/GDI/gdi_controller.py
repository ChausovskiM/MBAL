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
from code_MBAL.Density_MOD.Density_calc import Density_calc
from code_MBAL.Visc_MOD.Visc_calc import Visc_calc
from code_MBAL.Ld_MOD.Ld import Ld
from code_MBAL.Pust_MOD.Pust import Pust
from code_MBAL.Pust_MOD.Ld_MOD.Ld_calc import Ld_calc



def main():
    # открываем инпуты от листа PVT
    with open(r"code_sheets\PVT\pvt_input.json", 'r', encoding='utf-8') as f:
        pvt_props = json.load(f)
    #
    Z_method = 'пенг-робинсон'
    density_method = pvt_props["density_method"]
    viscosity_method = pvt_props["viscosity_method"]
    T_C_plast = pvt_props["T_plast_C"]
    #
    # Открываем инпуты от текущего листа ГДИ
    with open(r"code_sheets\GDI\gdi_input.json", 'r', encoding='utf-8') as f:
        gdi_input = json.load(f)
    #
    df_gdi_data = pd.DataFrame(gdi_input["gdi_data"]) #таблица ГДИ
    df_gdi_data['Pres2_bhp2'] = df_gdi_data['Pres']**2 - df_gdi_data['bhp']**2
    df_gdi_data['Pmean'] = (df_gdi_data['Pres'] + df_gdi_data['bhp'])/2
    #
    df_gdi_data['lmbda'] = df_gdi_data['Pmean'].apply(lambda p: Ld(Z_method, density_method, viscosity_method, p, T_C_plast))
    df_gdi_data['dP*lmbda'] = (df_gdi_data['Pres'] - df_gdi_data['bhp']) * df_gdi_data['lmbda']
    df_gdi_data['thp_calc'] = df_gdi_data.apply(lambda row: Pust(row['bhp'],
                                                                 row['q_gas'],
                                                                 gdi_input['d_nkt'],
                                                                 gdi_input['pipe_absolute_roughness'],
                                                                 gdi_input['gas_relative_density'], #D7
                                                                 gdi_input['well_md'],
                                                                 gdi_input['T_thp_C'],
                                                                 T_C_plast,
                                                                 Z_method, #D9
                                                                 viscosity_method,
                                                                 density_method,
                                                                 gdi_input['hydraulic_resistance_method'],
                                                                 gdi_input['hydraulic_resistance_coefficient'],
                                                                 gdi_input['well_tvd']                                                                 
                                                                 ),axis =1)
    # промежуточные столбцы для расчета последного столбца "Коэффициент гидравлического сопротивления"
    df_gdi_data['Zsr'] = df_gdi_data['bhp'].apply(lambda p: Z_calc(Z_method, p, (gdi_input['T_thp_C'] + T_C_plast)/2))
    df_gdi_data['density'] = df_gdi_data.apply(lambda row: Density_calc(density_method, row['bhp'], (gdi_input['T_thp_C'] + T_C_plast)/2, row['Zsr']),axis =1)
    df_gdi_data['visc'] = df_gdi_data.apply(lambda row: Visc_calc(viscosity_method, row['bhp'], (gdi_input['T_thp_C'] + T_C_plast)/2, row['Zsr'], ['density']),axis =1)
    # столбец "Коэффициент гидравлического сопротивления"
    df_gdi_data['coef_hidr_resistance'] = df_gdi_data.apply(lambda row: Ld_calc(gdi_input['hydraulic_resistance_method'], 
                                                                                row['q_gas'], 
                                                                                gdi_input['d_nkt'], 
                                                                                row['visc'], 
                                                                                row['density'], 
                                                                                gdi_input['pipe_absolute_roughness'], 
                                                                                gdi_input['hydraulic_resistance_coefficient']),axis =1)
    print(df_gdi_data[['lmbda','thp','thp_calc','coef_hidr_resistance']])
    #выгрузка результатов
    df_gdi_data.to_json('code_sheets/GDI/gdi_output.json', orient='records', lines=True)
     # Создаем фигуру с двумя подграфиками
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(19, 6))

    # Первый график:
    ax1.scatter(df_gdi_data['q_gas'], df_gdi_data['Pres2_bhp2'], marker='o', color='blue', label='Данные')
    ax1.set_xlabel('Дебит газа, тыс. м³/сут')
    ax1.set_ylabel('Pпл²-Pзаб², МПа²')
    ax1.set_ylim(bottom=0, top=df_gdi_data['Pres2_bhp2'].max() * 1.3)  # Ось Y начинается с 0
    ax1.set_xlim(0, None)

    # Квадратичная аппроксимация для первого графика
    x1 = df_gdi_data['q_gas']
    y1 = df_gdi_data['Pres2_bhp2']
    coeffs1 = np.polyfit(x1, y1, 2)
    poly1 = np.poly1d(coeffs1)
    x1_fit = np.linspace(x1.min(), x1.max(), 100)
    y1_fit = poly1(x1_fit)
    equation1 = f'y = {coeffs1[0]:.2e}x² + {coeffs1[1]:.2e}x + {coeffs1[2]:.2e}'
    ax1.plot(x1_fit, y1_fit, color='black', linewidth=1, linestyle='-', label=equation1)
    ax1.legend()
    ax1.grid(True)

    # Второй график:
    ax2.scatter(df_gdi_data['q_gas'], df_gdi_data['dP*lmbda'], marker='o', color='blue', label='Данные')
    ax2.set_xlabel('Дебит газа, тыс. м³/сут')
    ax2.set_ylabel('dP∙λ, МПа²/сП')
    ax2.set_ylim(bottom=0, top=df_gdi_data['dP*lmbda'].max() * 1.2)  # Ось Y начинается с 0
    ax2.set_xlim(0, None)

    # Квадратичная аппроксимация для второго графика
    x2 = df_gdi_data['q_gas']
    y2 = df_gdi_data['dP*lmbda']
    coeffs2 = np.polyfit(x2, y2, 2)
    poly2 = np.poly1d(coeffs2)
    x2_fit = np.linspace(x2.min(), x2.max(), 100)
    y2_fit = poly2(x2_fit)
    equation2 = f'y = {coeffs2[0]:.2e}x² + {coeffs2[1]:.2e}x + {coeffs2[2]:.2e}'
    ax2.plot(x2_fit, y2_fit, color='black', linewidth=1, linestyle='-', label=equation2)
    ax2.legend()
    ax2.grid(True)

    # Третий график:
    ax3.scatter(df_gdi_data['thp'], df_gdi_data['thp_calc'], marker='o', color='blue')
    ax3.set_xlabel('Устьевое давление (факт), МПа')
    ax3.set_ylabel('Устьевое давление (расчет), МПа')
    ax3.set_ylim(bottom=0, top=df_gdi_data['thp_calc'].max() * 1.2)  # Ось Y начинается с 0
    ax3.set_xlim(0, None)
    ax3.legend()
    ax3.grid(True)

    # Настройка общего заголовка и отступов
    plt.tight_layout()

    # Отображение графиков
    plt.show()
if __name__ == "__main__":
    main()