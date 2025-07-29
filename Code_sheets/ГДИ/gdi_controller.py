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

from code_MBAL.Ld_MOD.Ld import Ld
#
def calc_mixture_params(gas_components):
    """
    Вычисляет средние параметры смеси: молекулярный вес, критическую температуру и давление.

    Ожидается, что mol_fraction_pct передаётся в процентах (%).
    """
    Mw_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Mw"] for comp in gas_components)
    Tc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Tc"] for comp in gas_components)
    Pc_mix = sum(comp["mol_fraction_pct"] / 100 * comp["Pc"] for comp in gas_components)

    return  Pc_mix, Tc_mix, Mw_mix


def main():
    # открываем инпуты от листа PVT
    with open(r"code_sheets\PVT\input_properties.json", 'r', encoding='utf-8') as f:
        pvt_props = json.load(f)
    #
    Z_method = pvt_props["Z_method"]
    density_method = pvt_props["density_method"]
    viscosity_method = pvt_props["viscosity_method"]
    T_C_plast = pvt_props["T_plast_C"]
    #
    with open(r"code_sheets\PVT\gas_components.json", 'r', encoding='utf-8') as f:
        gas_components = json.load(f)
    Pc_mix, Tc_mix, Mw_mix = calc_mixture_params(gas_components)
    # Открываем инпуты от текущего листа PVT
    with open(r"code_sheets\GDI\gdi_input.json", 'r', encoding='utf-8') as f:
        gdi_input = json.load(f)
    #
    
    df_gdi_data = pd.DataFrame(gdi_input["gdi_data"]) #таблица ГДИ
    df_gdi_data['Pres2_bhp2'] = df_gdi_data['Pres']**2 - df_gdi_data['bhp']**2
    df_gdi_data['Pmean'] = (df_gdi_data['Pres'] + df_gdi_data['bhp'])/2
    #
    df_gdi_data['lmbda'] = df_gdi_data['Pmean'].apply(lambda p: Ld(Z_method, density_method, viscosity_method, p, T_C_plast, Pc_mix, Tc_mix, Mw_mix))
    df_gdi_data['dP*lmbda'] = (df_gdi_data['Pres'] - df_gdi_data['bhp']) * df_gdi_data['lmbda']
    # df_gdi_data['thp_calc'] = df_gdi_data.apply(lambda row: Pust(row['bhp'],
    #                                                              row['q_gas'],
    #                                                              gdi_input['d_nkt'],
    #                                                              gdi_input['pipe_absolute_roughness'],
    #                                                              gdi_input['gas_relative_density'], #D7
    #                                                              gdi_input['well_md'],
    #                                                              gdi_input['T_thp_C'],
    #                                                              T_C_plast,
    #                                                              Z_method, #D9
    #                                                              viscosity_method,
    #                                                              density_method,
    #                                                              gdi_input['hydraulic_resistance_method'],
    #                                                              gdi_input['hydraulic_resistance_coefficient'],
    #                                                              Pc_mix, Tc_mix, Mw_mix
    #                                                              ))

    print(df_gdi_data['lmbda'])
if __name__ == "__main__":
    main()