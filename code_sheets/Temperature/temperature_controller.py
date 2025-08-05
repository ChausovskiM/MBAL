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
from code_MBAL.TEMP_MOD.Tust import Tust

from code_MBAL.Pust_MOD.Ld_MOD.Ld_calc import Ld_calc

def main():
# Открываем инпуты от текущего листа Температура
    with open(r"code_sheets\Temperature\temperature_input.json", 'r', encoding='utf-8') as f:
        temp_input = json.load(f)
# Открываем инпуты/оутпуты от текущего листа PVT
    with open(r"code_sheets\PVT\pvt_input.json", 'r', encoding='utf-8') as f:
        pvt_input = json.load(f)
    T_C_plast = pvt_input["T_plast_C"]
    cond_density = pvt_input["condensate_density_kgm3"] #плотность конденсата
    #
    with open(r"code_sheets\PVT\pvt_output.json", 'r', encoding='utf-8') as f:
        pvt_output = json.load(f)
    relative_dens = pvt_output["gas_relative_density"] #отн плотность газа по воздуху
    density_input = pvt_output ["rho_std"] #Плотность газа (Плотность газа в стд условиях) 0.745
    #
    # === Расчет по формулам ==== F2:M2
    gp = temp_input["Qgas"]*1000/24*density_input
    go = temp_input["Qcondensate"]/24*cond_density
    t = temp_input["working_time"]*24 #время 
    # расчет Рустьевого
    P_ust = Pust(temp_input['bhp'],temp_input["Qgas"],temp_input["dnkt"],temp_input['pipe_absolute_roughness'],relative_dens,
                 temp_input['well_md'], temp_input['T_thp_C1'], T_C_plast, temp_input['Z_method'],temp_input['viscosity_method'],
                 temp_input['density_method'],temp_input['hydraulic_resistance_method'],temp_input['hydraulic_resistance_coefficient'],temp_input['well_tvd'])
    # расчет Т устьевого
    Temp_ust = Tust(T_C_plast,temp_input['Gp'],temp_input['well_tvd'],temp_input['lmbda_p'],t,
                    gp/(gp+go)*temp_input['cp_gas']+go/(gp+go)*temp_input['cp_condensate'],
                    temp_input['Rc'], (temp_input['Qgas']*1000*density_input + cond_density*temp_input['Qcondensate'])/24,
                    temp_input['Di'], temp_input['bhp']*10, P_ust*10, temp_input['well_tvd'], temp_input['A'], temp_input['Cp'],
                    temp_input['Gm'], temp_input['depth_frost'],temp_input['lmbda_m'],temp_input['Cpm'],temp_input['tm'],temp_input['tc.r'])
    # расчет оставшихся P2:S2
    # считаем новое Руст с Temp_ust и well_tvd а не well_md!
    P_ust1 = Pust(temp_input['bhp'],temp_input["Qgas"],temp_input["dnkt"],temp_input['pipe_absolute_roughness'],relative_dens,
                  temp_input['well_tvd'], Temp_ust, T_C_plast, temp_input['Z_method'],temp_input['viscosity_method'],
                  temp_input['density_method'],temp_input['hydraulic_resistance_method'],temp_input['hydraulic_resistance_coefficient'],temp_input['well_tvd'])
    #
    Temp_ust2 = Tust(T_C_plast,temp_input['Gp'],temp_input['well_tvd'],temp_input['lmbda_p'],t,
                     gp/(gp+go)*temp_input['cp_gas']+go/(gp+go)*temp_input['cp_condensate'],
                     temp_input['Rc'], (temp_input['Qgas']*1000*density_input + cond_density*temp_input['Qcondensate'])/24,
                     temp_input['Di'], temp_input['bhp']*10, P_ust1*10, temp_input['well_tvd'], temp_input['A'], temp_input['Cp'],
                     temp_input['Gm'], temp_input['depth_frost'],temp_input['lmbda_m'],temp_input['Cpm'],temp_input['tm'],temp_input['tc.r'])
    #
    P_ust2 = Pust(temp_input['bhp'],temp_input["Qgas"],temp_input["dnkt"],temp_input['pipe_absolute_roughness'],relative_dens,
                  temp_input['well_md'], Temp_ust2, T_C_plast, temp_input['Z_method'],temp_input['viscosity_method'],
                  temp_input['density_method'],temp_input['hydraulic_resistance_method'],temp_input['hydraulic_resistance_coefficient'],temp_input['well_tvd'])
    #
    Temp_ust3 = Tust(T_C_plast,temp_input['Gp'],temp_input['well_tvd'],temp_input['lmbda_p'],t,
                     gp/(gp+go)*temp_input['cp_gas']+go/(gp+go)*temp_input['cp_condensate'],
                     temp_input['Rc'], (temp_input['Qgas']*1000*density_input + cond_density*temp_input['Qcondensate'])/24,
                     temp_input['Di'], temp_input['bhp']*10, P_ust2*10, temp_input['well_tvd'], temp_input['A'], temp_input['Cp'],
                     temp_input['Gm'], temp_input['depth_frost'],temp_input['lmbda_m'],temp_input['Cpm'],temp_input['tm'],temp_input['tc.r'])
    #
    #print(Temp_ust,P_ust1,Temp_ust2,P_ust2,Temp_ust3)
    summary = {
        "T_ust":round(Temp_ust3,4),
        "P_ust":round(P_ust2,4),
        }

    with open('code_sheets/Temperature/temperature_outputs.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=4)                                                               
if __name__ == "__main__":
    main()