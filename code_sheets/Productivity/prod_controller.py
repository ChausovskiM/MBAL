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
from code_MBAL.Complementary_functions.OGR_calc import OGR_calc

def number(q, data_range):
    if q == 0:
        return 0
    i = 0
    for value in data_range:
        if pd.isna(value):
            break
        if q < value:
            i += 1
    return i + 1


def main():
    # Открываем инпуты от текущего листа Продуктивность
    with open(r"code_sheets\Productivity\prod_input.json", 'r', encoding='utf-8') as f:
        prod_input = json.load(f)
    ofp_gas = prod_input["ofp_gas"]
    kgf_method = prod_input["kgf_method"]
    df_w_table = pd.DataFrame(prod_input["well_table"])    
    # Открываем инпуты от текущего листа PVT
    with open(r"code_sheets\PVT\pvt_input.json", 'r', encoding='utf-8') as f:
        pvt_input = json.load(f)
    # 
    with open(r"code_sheets\PVT\pvt_output.json", 'r', encoding='utf-8') as f:
        pvt_output = json.load(f)
    relative_dens = pvt_output["gas_relative_density"] #отн плотность газа по воздуху
    T_C_plast = pvt_input["T_plast_C"]
    density_method = pvt_input["density_method"]
    visc_method = pvt_input["viscosity_method"]
    # Открываем инпуты от текущего листа ГДИ
    with open(r"code_sheets\PZ\pz_input.json", 'r', encoding='utf-8') as f:
        pz_input = json.load(f)
    Z_method = pz_input["Z_method"]
    #
    # расчет таблицы
    df_w_table = df_w_table.replace(np.nan,0) #для расчетов
    df_w_table['Leff'] =df_w_table.apply(lambda row: ((row['h_xy']**2 +row['h_z']**2)**0.5)*{0:1,row['NTG']:row['h_z']}[row['h_z']],axis=1) 
    df_w_table['Rkg'] =df_w_table.apply(lambda row: (row["Area"]*1e6/math.pi)**0.5,axis=1) #странная формула ексель!
    df_w_table['a_joshi'] = (df_w_table["Leff"]/2)*(0.5 + (0.25 + (2*df_w_table['Rkg']/df_w_table['Leff'])**4)**0.5)**0.5
    df_w_table['rw_joshi'] = (df_w_table['Rkg']*df_w_table['Leff']/2)/(df_w_table['a_joshi']*(1 + 
                                        (1 - (df_w_table['Leff']/2/df_w_table['a_joshi'])**2)**0.5)*((df_w_table['heff']/2/(df_w_table['Dzab']/2000))**(df_w_table['heff']/df_w_table['Leff'])))
    df_w_table['Dxy'] = (df_w_table['Area']*1e6)**0.5
    df_w_table['kh_xy'] = df_w_table['h_xy']*(df_w_table['k_xy']*df_w_table['k_z'])**0.5
    df_w_table['kh_xy_shtrih'] = 2*df_w_table['NTG']*df_w_table['h_xy']*df_w_table['k_xy']/math.pi
    df_w_table['kh_z'] = df_w_table[['NTG','h_z','k_xy']].prod(axis=1)
    df_w_table['Ro_xy'] = (0.28 * 
        np.sqrt((df_w_table['heff'] ** 2) * np.sqrt(df_w_table['k_xy'] / df_w_table['k_z']) + 
                (df_w_table['Dxy'] ** 2) * np.sqrt(df_w_table['k_z'] / df_w_table['k_xy'])) / 
        (np.sqrt(np.sqrt(df_w_table['k_xy'] / df_w_table['k_z'])) + np.sqrt(np.sqrt(df_w_table['k_z'] / df_w_table['k_xy']))))
    #
    df_w_table['Ro_xy_shtrih'] = 0.14 * np.sqrt((df_w_table['k_z'] + df_w_table['Dzab']/1000)**2 + df_w_table['Dxy']**2)
    df_w_table['Roz'] = 0.197 * df_w_table['Dxy']
    df_w_table['Txy'] = df_w_table['kh_xy'] / (np.log(df_w_table['Ro_xy'] / (df_w_table['Dzab']/1000/2)) - 0.75 + df_w_table['S'])
    df_w_table['Txy_shtrih'] = df_w_table['kh_xy_shtrih'] / (np.log(df_w_table['Ro_xy_shtrih'] / (df_w_table['Dzab']/1000/2)) - 0.75 + df_w_table['S'])
    df_w_table['Tz'] = df_w_table['kh_z'] / (np.log(df_w_table['Roz'] / (df_w_table['Dzab']/1000/2)) - 0.75 + df_w_table['S'])
    df_w_table['kh'] = np.sqrt(df_w_table[['kh_xy', 'kh_xy_shtrih']].max(axis=1)**2 + df_w_table['kh_z']**2)
    df_w_table['T'] = np.sqrt(df_w_table[['Txy', 'Txy_shtrih']].max(axis=1)**2 + df_w_table['Tz']**2)
    df_w_table['Rk'] = (df_w_table['Dzab']/1000/2) * np.exp(df_w_table['kh']/df_w_table['T'] - df_w_table['S'] + 0.75)
    df_w_table['betta'] = 1.88e10 * (df_w_table['k_xy']**(-1.47)) * (df_w_table['poro_frac']**(-0.53))
    #
    df_w_table['Z(Pzab)'] = df_w_table['Pzab'].apply(lambda p : Z_calc(Z_method,p,T_C_plast)) #ПРОМЕЖУТОЧНЫЙ
    df_w_table['mu(Pzab)'] = df_w_table.apply(lambda row : Visc_calc(visc_method,row['Pzab'],T_C_plast,row['Z(Pzab)'],
                                                                    Density_calc(density_method,row['Pzab'],T_C_plast,row['Z(Pzab)'])),axis =1)
    #
    df_w_table['F'] = 1.611e-13 * df_w_table['betta'] * (T_C_plast + 273.15) * relative_dens / df_w_table['mu(Pzab)'] / (df_w_table['Dzab']/1000/2) / (df_w_table['Leff']**2)
    df_w_table['Djhoshi1'] = 0.0077677 * df_w_table['F'] * ofp_gas * df_w_table['k_xy'] * df_w_table['heff'] / (T_C_plast + 273.15)
    df_w_table['Djhoshi2'] = 0.0077677 * df_w_table['F'] * ofp_gas * df_w_table['kh'] / (T_C_plast + 273.15)
    df_w_table['Pcp'] = np.sqrt((df_w_table['Pres']**2 + df_w_table['Pzab']**2) / 2)
    #
    df_w_table['Z(Pcp)'] = df_w_table['Pcp'].apply(lambda p : Z_calc(Z_method,p,T_C_plast))
    
    df_w_table['mu(Pcp)'] = df_w_table.apply(lambda row :  Visc_calc(visc_method,row['Pcp'],T_C_plast,row['Z(Pcp)'],
                                                                    Density_calc(density_method,row['Pcp'],T_C_plast,row['Z(Pcp)'])),axis =1)
    ###
    # Вычисляем части формулы
    part1 = (df_w_table['a_joshi'] + (df_w_table['a_joshi']**2 - (df_w_table['Leff']/2)**2)**0.5) / df_w_table['Leff'] * 2
    part2 = (df_w_table['k_xy'] / df_w_table['k_z'])**0.5 * df_w_table['heff'] / df_w_table['Leff'] * np.log((df_w_table['k_xy'] / df_w_table['k_z'])**0.5 * df_w_table['heff'] / (df_w_table['Dzab'] / 1000 / 2) / 2)
    part3 = np.log(part1) + part2 + df_w_table['S']

    # Вычисляем окончательное значение для столбца "a1"
    df_w_table['a1'] = 1 / (np.pi * df_w_table['k_xy'] * df_w_table['heff'] / df_w_table['mu(Pcp)'] /  df_w_table['Z(Pcp)'] * 1e-7 / part3 * 86400)
    ###
    df_w_table['b1'] = df_w_table['heff']**2 / df_w_table['Leff']**2 / 100
    df_w_table['a2'] = df_w_table.apply(
            lambda row: (273.15 + T_C_plast) * row['mu(Pcp)'] * row['Z(Pcp)'] * (np.log(row['Rkg'] / row['rw_joshi']) - 0.75 + row['S']) / 0.77677 / ofp_gas / row['k_xy'] / row['heff']
            if all(pd.notna(val) and val != 0 for val in [row['mu(Pcp)'], row['Z(Pcp)'], row['Rkg'], row['rw_joshi'], row['k_xy'], row['heff']])
            else 0, axis=1)
    df_w_table['b2'] = (273.15 + T_C_plast) * df_w_table['mu(Pcp)'] * df_w_table['Z(Pcp)'] * df_w_table['Djhoshi1'] / 0.77677 / ofp_gas / df_w_table['k_xy'] / df_w_table['heff']
    df_w_table['a3'] = ((273.15 + T_C_plast) * df_w_table['mu(Pcp)'] * df_w_table['Z(Pcp)'] *
            (np.log(df_w_table['Rk'] / (df_w_table['Dzab'] / 1000 / 2)) - 0.75 + df_w_table['S']) /0.77677 / ofp_gas / df_w_table['kh'])
    #
    df_w_table['b3'] = ((273.15 + T_C_plast) * df_w_table['mu(Pcp)'] * df_w_table['Z(Pcp)'] * df_w_table['Djhoshi2'] /0.77677 / ofp_gas / df_w_table['kh'])
    df_w_table['betta2'] = df_w_table.apply(lambda row: 1.88e10 * (row['k_frac']**(-1.47)) * (row['poro_frac']**(-0.53)) if row['k_frac']!=0 else 0,axis = 1)
    df_w_table['Dxy_frac'] = np.sqrt(np.pi * df_w_table['L/2']**2)
    df_w_table['popr_Dy_1plus2'] = df_w_table.apply(
            lambda row: (
                1 if row['Nfrac'] == 1 else
                (1 + (
                    (row['Dxy_frac'] - row['h_xy'] / row['Nfrac']) / row['Dxy_frac']
                    if row['Dxy_frac'] > row['h_xy'] / row['Nfrac'] else 1
                )) / 2
            ) if all(pd.notna(val) for val in [row['Nfrac'], row['Dxy_frac'], row['h_xy']]) and row['Nfrac'] != 0 else 0,axis=1) #вроде ок

    #
    df_w_table['T_frac1plus2'] = df_w_table.apply(
            lambda row: (
                8 * (2 if row['Nfrac'] > 2 else row['Nfrac']) * row['k_xy_frac'] * row['Dxy_frac'] * row['heff'] /
                (row['Dxy_frac'] * row['popr_Dy_1plus2'] + (row['S'] * row['Dxy_frac'] * row['popr_Dy_1plus2'] / np.pi)) / 2 / np.pi
            ) if all(pd.notna(val) for val in [row['Nfrac'], row['k_xy_frac'], row['Dxy_frac'], row['heff'], row['popr_Dy_1plus2'], row['S']]) and row['Dxy_frac'] != 0 else 0,axis=1)
    #
    df_w_table['popr_Dy_3'] = df_w_table.apply(
            lambda row: (
                (row['Dxy_frac'] - row['h_xy'] / row['Nfrac']) / row['Dxy_frac']
                if row['Dxy_frac'] > row['h_xy'] / row['Nfrac'] else 1
            ) if all(pd.notna(val) for val in [row['Dxy_frac'], row['h_xy'], row['Nfrac']]) and row['Nfrac'] != 0 else 0,axis=1)
    #
    df_w_table['T_frac3+'] = df_w_table.apply(
            lambda row: (
                8 * (row['Nfrac'] - 2 if row['Nfrac'] > 2 else 0) * row['k_xy_frac'] * row['Dxy_frac'] * row['heff'] /
                (row['Dxy_frac'] * row['popr_Dy_3'] + (row['S'] * row['Dxy_frac'] * row['popr_Dy_3'] / np.pi)) / 2 / np.pi
            ) if all(pd.notna(val) for val in [row['Nfrac'], row['k_xy_frac'], row['Dxy_frac'], row['heff'], row['popr_Dy_3'], row['S']]) and row['Dxy_frac'] != 0 else 0,axis=1)
    #
    df_w_table['R_frac'] = (df_w_table['Dxy_frac'] * ( df_w_table['Dxy_frac'] + np.where(df_w_table['Nfrac'] > 1, df_w_table['h_xy'] * (df_w_table['Nfrac'] - 1) / (df_w_table['Nfrac'] + 1), 0)) / np.pi)**0.5
    df_w_table['a1_m'] = (df_w_table['Dzab'] / 1000) / np.sin(np.radians(df_w_table['teta'] + 0.00001))
    df_w_table['a2_m'] = (df_w_table['Dzab'] * df_w_table['h_z'] / (df_w_table['h_xy'] + df_w_table['Dzab']/1000) / 1000) + df_w_table['Dzab']/1000
    df_w_table['hp'] = df_w_table['Nfrac'] * (df_w_table['a1_m']**2 + df_w_table['a2_m']**2)**0.5
    df_w_table['hp_corr'] = np.where(
            df_w_table['hp'] > (df_w_table['h_xy']**2 + df_w_table['h_z']**2)**0.5,
            (df_w_table['h_xy']**2 + df_w_table['h_z']**2)**0.5,
            df_w_table['hp'])
    df_w_table['F_frac'] = np.where(
            (df_w_table['betta2'] > 0) & (df_w_table['mu(Pzab)'] > 0) & (df_w_table['w_frac'] > 0),
            1.611e-13 * df_w_table['betta2'] * (273.15 + T_C_plast) * relative_dens / df_w_table['mu(Pzab)'] / (2 * df_w_table['w_frac'] / np.pi / 1000) / (df_w_table['hp_corr']**2), 0)
    df_w_table['D_frac'] = 0.0077677 * df_w_table['F_frac'] * df_w_table['k_xy_frac'] * ofp_gas * df_w_table['heff'] / (273.15 + T_C_plast) #BN
    #
    df_w_table['b_frac'] = np.where(
            (df_w_table['mu(Pcp)'] > 0) & (df_w_table['Z(Pcp)'] > 0) & (df_w_table['D_frac'] > 0) & (df_w_table['k_xy_frac'] > 0),
            (273.15 + T_C_plast) * df_w_table['mu(Pcp)'] * df_w_table['Z(Pcp)'] * df_w_table['D_frac'] / 0.77677 / df_w_table['k_xy_frac'] / ofp_gas / df_w_table['heff'], 0)
    df_w_table['a_fr'] = np.where(
            (df_w_table['T_frac1plus2'] + df_w_table['T_frac3+']) > 0,
            (273.15 + T_C_plast) * df_w_table['mu(Pcp)'] * df_w_table['Z(Pcp)'] / 0.77677 / (df_w_table['T_frac1plus2'] + df_w_table['T_frac3+']) / ofp_gas ,0)
    #
    log_term = np.where(df_w_table['R_frac']!=0, np.log(df_w_table['Rkg'] / df_w_table['R_frac']) - 0.75, 0) #проверка на неравенство нуля
    df_w_table['a_dren'] = np.where(
            (log_term > 0) & (df_w_table['k_xy'] > 0) & (df_w_table['heff'] > 0),
            (273.15 + T_C_plast) * df_w_table['mu(Pcp)'] * df_w_table['Z(Pcp)'] * log_term / 0.77677 / ofp_gas / df_w_table['k_xy'] / df_w_table['heff'],0)
    #
    df_w_table['a_summ'] = df_w_table[['a_fr','a_dren']].sum(axis=1)
    #
    discriminant = df_w_table['a_summ']**2 + 4 * df_w_table['b_frac'] * (df_w_table['Pres']**2 - df_w_table['Pzab']**2)
    df_w_table['q_iter1'] = np.where(
            (df_w_table['b_frac'] > 0) & (discriminant >= 0),
            (-df_w_table['a_summ'] + discriminant**0.5) / 2 / df_w_table['b_frac'],0)
    #
    df_w_table['P_temp1'] = np.sqrt(df_w_table['Pres']**2 - df_w_table['a_dren'] * df_w_table['q_iter1'] - df_w_table['b_frac'] * df_w_table['q_iter1']**2)
    #   
    df_w_table['P_temp2'] = np.sqrt(df_w_table['a_fr'] * df_w_table['q_iter1'] + df_w_table['b_frac'] * df_w_table['q_iter1']**2 + df_w_table['Pzab']**2)
    #
    df_w_table['P_sred'] = (df_w_table['P_temp1'] + df_w_table['P_temp2']) / 2
    #
    df_w_table['P_sr'] = np.sqrt((df_w_table['P_sred']**2 + df_w_table['Pzab']**2) / 2)
    #
    df_w_table['Z(P_sr)'] = df_w_table['P_sr'].apply(lambda p : Z_calc(Z_method,p,T_C_plast))
    #
    df_w_table['mu(P_sr)'] = df_w_table.apply(lambda row :  Visc_calc(visc_method,row['P_sr'],T_C_plast,row['Z(P_sr)'],Density_calc(density_method,row['P_sr'],T_C_plast,row['Z(P_sr)'])),axis =1)
    #
    df_w_table['a_fr2'] = df_w_table.apply(
            lambda row: (
                (273.15 + T_C_plast) * row['mu(P_sr)'] * row['Z(P_sr)'] / 0.77677 / (row['T_frac1plus2'] + row['T_frac3+'])
            ) if all(pd.notna(val) for val in [row['mu(P_sr)'], row['Z(P_sr)'], row['T_frac1plus2'], row['T_frac3+']]) and (row['T_frac1plus2'] + row['T_frac3+']) != 0 else 0,axis=1)
    #
    df_w_table['a_dren2'] = df_w_table.apply(
            lambda row: (
                (273.15 + T_C_plast) * row['mu(P_sr)'] * row['Z(P_sr)'] * max(0, np.log(row['Rkg'] / row['R_frac']) - 0.75) / 0.77677 / ofp_gas / row['k_xy'] / row['heff']
            ) if all(pd.notna(val) for val in [row['mu(P_sr)'], row['Z(P_sr)'], row['Rkg'], row['R_frac'], row['k_xy'], row['heff']]) and row['k_xy'] != 0 and row['heff'] != 0 and row['R_frac']!= 0 else 0,axis=1)
    #
    df_w_table['a_summ2'] = df_w_table[['a_fr2','a_dren2']].sum(axis=1)
    #
    # РАСЧЕТ А И В ДЛЯ КВАДРАТНОГО УРАВНЕНИЯ
    pi_method = prod_input["pi_method"]
    df_w_table['A_2param'] = df_w_table.apply(
            lambda row: (
                row['a_summ2'] if row['Nfrac'] > 0 else (
                    np.mean([row['a1'], row['a3']]) if pi_method == "двухпараметрическая" else (
                        row['a1'] if pi_method == "joshi" else (
                            row['a3'] if pi_method == "peacemen" else (
                                np.mean([row['a1'], row['a2'], row['a3']]) if row['a2'] > 0 else np.mean([row['a1'], row['a3']])
                            )
                        )
                    )
                )
            ) if all(pd.notna(val) for val in [row['Nfrac'], row['a_summ2'], row['a1'], row['a3'], row['a2']]) else 0,axis=1)
    # 
    df_w_table['B_2param'] = df_w_table.apply(
            lambda row: (
                row['b_frac'] if row['Nfrac'] > 0 else (
                    np.mean([row['b2'], row['b3']]) if pi_method == "двухпараметрическая" else (
                        row['b1'] if pi_method == "joshi" else (
                            row['b3'] if pi_method == "peacemen" else (
                                row['b_frac'] if row['Nfrac'] > 0 else (
                                    np.mean([row['b1'], row['b2'], row['b3']]) if row['b1'] < 0.0001 else np.mean([row['b2'], row['b3']])
                                )
                            )
                        )
                    )
                )
            ) if all(pd.notna(val) for val in [row['Nfrac'], row['b_frac'], row['b1'], row['b2'], row['b3']]) else 0,axis=1)
    # 
    df_w_table['Qgas_2param'] = df_w_table.apply(
            lambda row: (
                (-1 * row['A_2param'] + (row['A_2param']**2 + 4 * row['B_2param'] * (row['Pres']**2 - row['Pzab']**2))**0.5) / (2 * row['B_2param'])
            ) if all(pd.notna(val) for val in [row['A_2param'], row['B_2param'], row['Pres'], row['Pzab']]) and row['B_2param'] != 0 else 0, axis=1) #тыс м3/сут
    #
    df_w_table['Qcondensate'] = df_w_table.apply(lambda row: OGR_calc(kgf_method,(row['Pres']+row['Pzab'])/2)*row['Qgas_2param']/1000, axis=1)
    # А и В для псевдодавлений
    df_w_table['Psr_for_lmbd'] = (df_w_table['Pres'] + df_w_table['Pzab'])/2
    df_w_table['A_pseudo'] = df_w_table['A_2param']/df_w_table['mu(Pcp)']/df_w_table['Z(Pcp)']/2
    df_w_table['B_pseudo'] = df_w_table['B_2param']/df_w_table['mu(Pcp)']/df_w_table['Z(Pcp)']/2
    #
    #
    df_w_table['lmbd(Psr)'] = df_w_table.apply(
            lambda row: (
                row['Psr_for_lmbd'] / (
                    Z_calc(Z_method, row['Psr_for_lmbd'], T_C_plast) *
                    Visc_calc(visc_method, row['Psr_for_lmbd'], T_C_plast, Z_calc(Z_method, row['Psr_for_lmbd'], T_C_plast),
                              Density_calc(density_method, row['Psr_for_lmbd'], T_C_plast, Z_calc(Z_method, row['Psr_for_lmbd'], T_C_plast)))
                )
            ) if all(pd.notna(val) for val in [row['Psr_for_lmbd']]) else 0, axis=1)
    
    df_w_table['Qgas_pseudo'] = df_w_table.apply(
            lambda row: (
                (-1 * row['A_pseudo'] + (row['A_pseudo']**2 + 4 * row['B_pseudo'] * ((row['Pres'] - row['Pzab']) * row['lmbd(Psr)']))**0.5) / (2 * row['B_pseudo'])
            ) if all(pd.notna(val) for val in [row['A_pseudo'], row['B_pseudo'], row['Pres'], row['Pzab'], row['lmbd(Psr)']]) and row['B_pseudo'] != 0 else 0,axis=1)
    #
    df_w_table['drill_ranking'] = df_w_table['Qgas_2param'].apply(lambda q: number(q, df_w_table['Qgas_2param']))
    #
    summary = {
        # добавить Оценка изменения А и В от от времени остановки скважин
        "results_table": df_w_table.to_dict(orient="list") 
    }
    with open('code_sheets/Productivity/productivity_output.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=4)
    #print(df_w_table[['A_pseudo','B_pseudo','Qgas_pseudo','drill_ranking']])
    #print(df_w_table['lmbd(Psr)'].values[0])


if __name__ == "__main__":
    main()