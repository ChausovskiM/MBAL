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
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from calendar import monthrange

#
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from code_MBAL.Ld_MOD.Ld import Ld
from code_MBAL.Q_MOD.fQLd import fQLd
from code_MBAL.Q_MOD.fQ import fQ
from code_MBAL.MBAL_fP_MOD.MBAL_fP import MBAL_fP
from code_MBAL.Pust_MOD.Pust import Pust
from code_MBAL.Tochigin_MOD.Tochigin import Tochigin
from code_MBAL.Z_MOD.Z_calc import Z_calc
from code_MBAL.Complementary_functions.OGR_calc import OGR_calc
from code_MBAL.Velosity_MOD.Velosity import Velosity
from code_MBAL.Complementary_functions.Composition_MOD.Composition_calc import Composition_calc


# from code_MBAL.Ld_MOD.Ld import Ld
# from code_MBAL.Pust_MOD.Pust import Pust
# from code_MBAL.TEMP_MOD.Tust import Tust

# from code_MBAL.Pust_MOD.Ld_MOD.Ld_calc import Ld_calc

def calculate_date(date_str):
    try:
        # Преобразуем строку в объект даты
        c3 = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Вычисляем новую дату
        new_date = date(year = c3.year - 1, month=1, day=1)
    except:
        # В случае ошибки возвращаем текущую дату
        new_date = date.today()

    return new_date

def increment_year_to_january(date_str):
    # Преобразуем строку в объект даты
    input_date = datetime.strptime(date_str, "%Y-%m-%d")

    # Увеличиваем год на 1 и устанавливаем месяц и день на январь и 1
    output_date = datetime(year=input_date.year + 1, month=1, day=1)

    return output_date

# Функция для определения количества дней в месяце
def days_in_month(date):
    year = date.year
    month = date.month
    return monthrange(year, month)[1]

def main():
    # инпуты листа PVT
    with open(r"code_sheets\PVT\pvt_input.json", 'r', encoding='utf-8') as f:
        pvt_input = json.load(f) 
    # Оутпут листа PVT
    with open(r"code_sheets\PVT\pvt_output.json", 'r', encoding='utf-8') as f:
        pvt_output = json.load(f)    
    # инпуты листа PZ
    with open(r"code_sheets\PZ\pz_input.json", 'r', encoding='utf-8') as f:
        pz_input = json.load(f)
    start_dev_date = pz_input["start_dev_date"]
    start_predcit_date = pz_input["start_predict_date"]
    #
    # Инпуты листа БАЗА
    with open(r"code_sheets\Base\base_input.json", 'r', encoding='utf-8') as f:
        base_input = json.load(f)
    df_tabl = pd.DataFrame(base_input["table_data"])
    # Оутпуты листа Продуктивность
    with open(r"code_sheets\Productivity\productivity_output.json", 'r', encoding='utf-8') as f:
        product_outputs_df = pd.DataFrame(json.load(f)["results_table"])
    #
    # определяем 1) Давление начала конденсации 2) Начальный КГФ
    if base_input['kgf_method'] == "experimental data":
        # Инпуты листа КГФ - ЭКСПЕРИМЕНТАЛЬНАЯ ЗАВИСИМОСТЬ
        with open(r"code_sheets\KGF\kgf_experimental_input.json", encoding="utf-8") as f:
            kgf_exp_input = json.load(f)
        Pnk, kgf = kgf_exp_input['Pnk'], kgf_exp_input['Pnk']
        # Оутпут листа КГФ
        with open(r"code_sheets\KGF\kgf_output.json", encoding="utf-8") as f:
            kgf_output = json.load(f)
        kgf = kgf_output['C5_plus']
    elif base_input['kgf_method'] == "typical dependence": 
        # Инпуты листа КГФ - ТИПОВАЯ ЗАВИСИМОСТЬ
        with open(r"code_sheets\KGF\kgf_typical_input.json", encoding="utf-8") as f:
            kgf_type_input = json.load(f)
            Pnk, kgf = kgf_type_input['Pnk'], kgf_type_input['KGF'] 
    #
    # дополняем таблицу месяцами - 6 лет по месяцам - 72 месяца
    for i in range(14,1201):
        df_tabl.loc[i-1,["month","exploration_coeff","dP"]] = [i,base_input["default_exploration_coeff"],2.6] #заполнение оставшихся месяцев
    #
    year_start = datetime(year = datetime.strptime(start_predcit_date, "%Y-%m-%d").year, month=12, day=1)
    df_tabl['date'] = df_tabl['month'].apply(lambda x: year_start + relativedelta(months=x))
    #
    # Накопленное время с начала разработки залежи
    df_tabl['cum_time'] = (df_tabl['date'] - datetime.strptime(start_dev_date, "%Y-%m-%d")).dt.days
    #
    # Продолжительность отчетного периода
    df_tabl['len_report_period'] = df_tabl['date'].apply(days_in_month)
    #
    # Выбытие базового фонда
    df_tabl['leave_base_fond'] = 0 #в этих ячейках не было формулы!нули Уточнить
    # Время работы выбывших скважин
    df_tabl['time_prod_leaving_wells'] = 0 #в этих ячейках не было формулы!нули Уточнить
    # Ввод скважин в NNNN году
    df_tabl['vvod_wells_in_curr_period'] = 0
    #
    # Действующий базовый фонд на начало периода/на конец периода
    df_tabl = df_tabl.assign(rab_fond_on_start_period = 0, rab_fond_on_end_period = 0) # Инициализируем столбцы
    df_tabl.loc[0,'rab_fond_on_start_period'] = base_input['entry_wells']
    # Рассчитываем значения
    for i in df_tabl.index:
        if i == 0:
            # Для первого периода используем начальное значение
            df_tabl.loc[i, 'rab_fond_on_end_period'] = (df_tabl.loc[i, 'vvod_wells_in_curr_period'] - df_tabl.loc[i, 'leave_base_fond'] + df_tabl.loc[i, 'rab_fond_on_start_period'])
        else:
            # Для последующих периодов используем значение за предыдущий период
            df_tabl.loc[i, 'rab_fond_on_start_period'] = df_tabl.loc[i-1, 'rab_fond_on_end_period']
            df_tabl.loc[i, 'rab_fond_on_end_period'] = (df_tabl.loc[i, 'vvod_wells_in_curr_period'] - df_tabl.loc[i, 'leave_base_fond'] + df_tabl.loc[i, 'rab_fond_on_start_period'])

    #Общее время работы скважин
    df_tabl['all_time_inprod'] = df_tabl['len_report_period']*df_tabl['rab_fond_on_end_period'] + df_tabl['leave_base_fond']*df_tabl['time_prod_leaving_wells']
    #
    # Среднедействующий базовый фонд
    df_tabl['mean_rab_basefond'] = df_tabl['all_time_inprod']/ df_tabl['len_report_period'] * df_tabl['exploration_coeff']
    #
    # Накопленная добыча газа на начало/конец периода
    df_tabl = df_tabl.assign(Qcum_gas_start_period = 0.0, Qcum_gas_end_period = 0.0) # Инициализируем столбцы
    # 
    # А фильтр-й коэф-т (база), B фильтр-й коэф-т (база)
    df_tabl['A'],df_tabl['B'] = product_outputs_df['A_2param'].values[0],product_outputs_df['B_2param'].values[0]
    #
    # Составляющие добычи Г и К по фондам
    df_tabl = df_tabl.assign(Qgas_vns=0.0,Qgas_frac=0.0,Qgas_pvlg=0.0,Qgas_zbs=0.0,Qgas_rs=0.0,Qgas_vbd=0.0,Qgas_gtm=0.0,Qgas_periodic=0.0,         #столбцы добычи газа из разного фонда
                             Qcond_vns=0.0,Qcond_frac=0.0,Qcond_pvlg=0.0,Qcond_zbs=0.0,Qcond_rs=0.0,Qcond_vbd=0.0,Qcond_gtm=0.0,Qcond_periodic=0.0) #столбцы добычи кондера из разного фонда
    #  
    # расчет Рпл и Qнакоп на начало и конец периода
    for i in df_tabl.index: # по строкам
        if i == 0: #самый 1-ый месяц
            df_tabl.loc[i,'Qcum_gas_start_period'] = float(pz_input['Cum_gas_under_pred']) #достаём из словаря (Qнакоп на начало периода)
            #
            # Pпл на начало периода
            df_tabl.loc[i,'Ppl_on_start_period'] = MBAL_fP(pz_input['P_reservor_init'], pz_input['T_reservor_init'], 
                                                        Z_calc(pvt_input["Z_method"],pz_input['P_reservor_init'],pz_input['T_reservor_init']), 
                                                        pz_input['nbz_gas'], 
                                                        df_tabl.loc[i,'Qcum_gas_start_period'], pz_input['pore_comp'], pz_input['water_comp'], pz_input["aquifer_permeability"], 
                                                        pz_input["aquifer_porosity"], pz_input["aquifer_radius"], pz_input["aquifer_thickness"],df_tabl.loc[i,'cum_time'],  
                                                        pz_input["drainage_angle"], pz_input["water_viscosity"], pz_input["sw"],pvt_input["Z_method"])
            # Забойное давление
            df_tabl.loc[i,'Pzab'] = df_tabl.loc[i,'Ppl_on_start_period'] - df_tabl.loc[i,'dP']
            # 
            # расчет лямбды через ld
            df_tabl.loc[i,'lmbda'] = Ld(pvt_input["Z_method"], pvt_input["density_method"], base_input["viscosity_method"],(df_tabl.loc[i,'Ppl_on_start_period']+df_tabl.loc[i,'Pzab'])/2, pz_input['T_reservor_init'])
            #
            # Дебит газа базовых скважин
            if df_tabl.loc[i, 'mean_rab_basefond'] > 0:
                if base_input["qgas_method"] == 'типовая зависимость':
                    df_tabl.loc[i, 'debit_gaza_base'] = fQ(df_tabl.loc[i, 'A'], df_tabl.loc[i, 'B'], df_tabl.loc[i, 'Ppl_on_start_period'], df_tabl.loc[i, 'Pzab'])
                else:
                    df_tabl.loc[i, 'debit_gaza_base'] = fQLd(df_tabl.loc[i, 'A'], df_tabl.loc[i, 'B'], df_tabl.loc[i, 'lmbda'],df_tabl.loc[i, 'Ppl_on_start_period'], df_tabl.loc[i, 'Pzab'])
            else:
                df_tabl.loc[i, 'debit_gaza_base'] = 0
            #
            # Добыча газа из базовых скважин
            df_tabl.loc[i,'Qgas_base_fond'] = df_tabl.loc[i,['len_report_period','mean_rab_basefond','debit_gaza_base']].prod()/1000
            #
            # Добыча газа всего
            df_tabl.loc[i,'Qgas_all'] = df_tabl.loc[i,['Qgas_base_fond','Qgas_vns','Qgas_frac','Qgas_pvlg','Qgas_zbs','Qgas_rs','Qgas_vbd','Qgas_gtm','Qgas_periodic']].sum()
            #          
            # Qнакоп на конец периода
            df_tabl.loc[i,'Qcum_gas_end_period'] = df_tabl.loc[i,['Qcum_gas_start_period','Qgas_all']].sum()
            #
            # Pпл на конец периода
            df_tabl.loc[i,'Ppl_on_end_period'] = MBAL_fP(pz_input['P_reservor_init'], pz_input['T_reservor_init'], 
                                                    Z_calc(pvt_input["Z_method"],pz_input['P_reservor_init'],pz_input['T_reservor_init']), 
                                                    pz_input['nbz_gas'], 
                                                    df_tabl.loc[i,'Qcum_gas_end_period'], pz_input['pore_comp'], pz_input['water_comp'], pz_input["aquifer_permeability"], 
                                                    pz_input["aquifer_porosity"], pz_input["aquifer_radius"], pz_input["aquifer_thickness"],
                                                    (df_tabl.loc[i,'cum_time']+df_tabl.loc[i,'len_report_period']),  #тут прибавляется продолжительность месяца
                                                    pz_input["drainage_angle"], pz_input["water_viscosity"], pz_input["sw"],pvt_input["Z_method"])
        else: # следующие индексы после 0
            # Для последующих периодов используем значение за предыдущий период
            df_tabl.loc[i,'Qcum_gas_start_period'] = df_tabl.loc[i-1, 'Qcum_gas_end_period']
            df_tabl.loc[i,'Ppl_on_start_period'] = df_tabl.loc[i-1,'Ppl_on_end_period']
            df_tabl.loc[i,'Pzab'] = df_tabl.loc[i,'Ppl_on_start_period'] - df_tabl.loc[i,'dP']
            df_tabl.loc[i,'lmbda'] = Ld(pvt_input["Z_method"], pvt_input["density_method"], base_input["viscosity_method"],(df_tabl.loc[i,'Ppl_on_start_period']+df_tabl.loc[i,'Pzab'])/2, pz_input['T_reservor_init'])
             # Дебит газа базовых скважин
            if df_tabl.loc[i, 'mean_rab_basefond'] > 0:
                if base_input["qgas_method"] == 'типовая зависимость':
                    df_tabl.loc[i, 'debit_gaza_base'] = fQ(df_tabl.loc[i, 'A'], df_tabl.loc[i, 'B'], df_tabl.loc[i, 'Ppl_on_start_period'], df_tabl.loc[i, 'Pzab'])
                else:
                    df_tabl.loc[i, 'debit_gaza_base'] = fQLd(df_tabl.loc[i, 'A'], df_tabl.loc[i, 'B'], df_tabl.loc[i, 'lmbda'],df_tabl.loc[i, 'Ppl_on_start_period'], df_tabl.loc[i, 'Pzab'])
            else:
                df_tabl.loc[i, 'debit_gaza_base'] = 0
            df_tabl.loc[i,'Qgas_base_fond'] = df_tabl.loc[i,['len_report_period','mean_rab_basefond','debit_gaza_base']].prod()/1000
            df_tabl.loc[i,'Qgas_all'] = df_tabl.loc[i,['Qgas_base_fond','Qgas_vns','Qgas_frac','Qgas_pvlg','Qgas_zbs','Qgas_rs','Qgas_vbd','Qgas_gtm','Qgas_periodic']].sum()
            df_tabl.loc[i,'Qcum_gas_end_period'] = df_tabl.loc[i,['Qcum_gas_start_period','Qgas_all']].sum()
            df_tabl.loc[i,'Ppl_on_end_period'] = MBAL_fP(pz_input['P_reservor_init'], pz_input['T_reservor_init'], 
                                                Z_calc(pvt_input["Z_method"],pz_input['P_reservor_init'],pz_input['T_reservor_init']), 
                                                pz_input['nbz_gas'], 
                                                df_tabl.loc[i,'Qcum_gas_end_period'], pz_input['pore_comp'], pz_input['water_comp'], pz_input["aquifer_permeability"], 
                                                pz_input["aquifer_porosity"], pz_input["aquifer_radius"], pz_input["aquifer_thickness"],
                                                (df_tabl.loc[i,'cum_time']+df_tabl.loc[i,'len_report_period']),  #тут прибавляется продолжительность месяца
                                                pz_input["drainage_angle"], pz_input["water_viscosity"], pz_input["sw"],pvt_input["Z_method"])
    # Среднее пластовое давление        
    df_tabl['Ppl_mean'] = (df_tabl['Ppl_on_start_period']+df_tabl['Ppl_on_end_period'])/2
    # ================================== КОНДЕНСАТ =================================
    # КГФ г/м3
    df_tabl['KGF'] = df_tabl.apply(lambda row: OGR_calc(base_input['kgf_method'], (row['Pzab'] + row['Ppl_mean'])/2),axis=1)
    #
    # Дебит конденсата базовых скважин м3/сут
    df_tabl['debit_cond_base_t'] = df_tabl['debit_gaza_base']*df_tabl['KGF']/1000
    #
    # Дебит конденсата базовых скважин т/сут
    df_tabl['debit_cond_base_m3'] = df_tabl['debit_cond_base_t']*base_input['condensate_density_kgm3']*1000
    #
    # Добыча конденсата из базовых скважин тыс.т
    df_tabl['Qcond_base_fond'] = df_tabl[['len_report_period','mean_rab_basefond','debit_cond_base_t']].prod(axis=1)/1000
    #
    # Добыча конденсата всего тыс т
    df_tabl['Qcond_all'] = df_tabl[['Qcond_base_fond','Qcond_vns','Qcond_frac','Qcond_pvlg','Qcond_zbs','Qcond_rs','Qcond_vbd','Qcond_gtm','Qcond_periodic']].sum(axis=1)
    #
    # Накопленная добыча конденсата на конец периода тыс.т
    df_tabl['Qcum_cond_end_period'] = df_tabl['Qcond_all'].cumsum()
    # ==============================================================================
    # ОИЗ газ/конденсат
    df_tabl = df_tabl.assign(oiz_gas = 0.0, oiz_cond = 0.0)
    oiz_gas = pz_input['nbz_gas'] - pz_input['Cum_gas_under_pred'] #оизы на дату начала прогноза(расчета)
    oiz_cond = pz_input['nbz_gas']*kgf/1000  #оизы конденсата на дату начала прогноза (расчета)
    df_tabl.loc[0,'oiz_gas']= oiz_gas - df_tabl['Qgas_all'].iloc[0]
    df_tabl.loc[1:,'oiz_gas'] = df_tabl['oiz_gas'].iloc[0] - df_tabl.loc[1:,'Qgas_all'].cumsum()
    df_tabl['oiz_cond'] = oiz_cond - df_tabl['Qcum_cond_end_period']
    #
    # Устьевое давление (m-gas_relative_density)
    df_tabl['Pust'] = df_tabl.apply(lambda row: Pust(row['Pzab'],row['debit_gaza_base'],base_input['d_nkt'],base_input['pipe_absolute_roughness'],pvt_output['gas_relative_density'],
                                                     base_input['well_tvd'],base_input['T_ust'],pz_input['T_reservor_init'],pvt_input["Z_method"], 
                                                     base_input["viscosity_method"],pvt_input["density_method"],base_input['hydraulic_resistance_method'],
                                                     base_input['hydraulic_resistance_coefficient'],base_input['well_tvd']),axis =1)
    # Минимальная скорость для выноса жидкости (Точигин)
    df_tabl['vmin_Tochigin'] = df_tabl.apply(lambda row: Tochigin(row['Pzab'],pz_input['T_reservor_init'],base_input['sigm_water'],base_input['condensate_density_kgm3'],
                                                                  base_input['d_nkt'],pvt_input['Z_method'],pvt_input["density_method"],pvt_output['gas_relative_density']),axis=1)
    #
    # Скорость на забое
    df_tabl['v_zab'] = df_tabl.apply(lambda row: Velosity(pvt_input['Z_method'],pz_input['T_reservor_init'],row['debit_gaza_base'],
                                                                  row['Pzab'],base_input['d_nkt']),axis =1)
    #  Скорость на устье
    df_tabl['v_ust'] = df_tabl.apply(lambda row: Velosity(pvt_input['Z_method'],base_input['T_ust'],row['debit_gaza_base'],
                                                                  row['Pust'],base_input['d_nkt']),axis =1)
    # Обеспечен вынос жидкости
    df_tabl['result'] = df_tabl.apply(lambda row: ("да" if row['v_zab'] > row['vmin_Tochigin'] else "нет") if row['debit_gaza_base'] > 0 else "",axis=1)
    #
    # Содержание C3-C4 в объеме пластового газа
    #загрузка данных композиционного состава
    with open(r"code_sheets\PVT\gas_components.json", encoding="utf-8") as f:
        gas_components = pd.DataFrame(json.load(f))
    # E11,E12,E13 с листа PVT
    Mw_propan = gas_components[gas_components['formula']=='C3H8']['Mw'].values[0],
    Mw_izobutan = gas_components[gas_components['formula']=='i-C4H10']['Mw'].values[0],
    Mw_nbutan = gas_components[gas_components['formula']=='n-C4H10']['Mw'].values[0],    
    # Давление начала конденсации
    
    #
    # Рассчитываем три компонента формулы 
    # 
    components = ["N2","CO2","H2S","H2","H2O","He","C1","C2H6","C3H8","i-C4H10","n-C4H10","C5+"] # 0-11
    #
    comp1 = df_tabl['Ppl_mean'].apply(lambda p: Composition_calc(p,Pnk,base_input['kgf_method'],gas_components['mol_fraction_pct'],8,base_input['composition_method']))
    comp2 = df_tabl['Ppl_mean'].apply(lambda p: Composition_calc(p,Pnk,base_input['kgf_method'],gas_components['mol_fraction_pct'],9,base_input['composition_method']))
    comp3 = df_tabl['Ppl_mean'].apply(lambda p: Composition_calc(p,Pnk,base_input['kgf_method'],gas_components['mol_fraction_pct'],10,base_input['composition_method']))
    df_tabl['c3_c4'] = (comp1*Mw_propan + comp2*Mw_izobutan + comp3*Mw_nbutan) * 10 / 24.04                                                      
    #
    # Оценка объема добычи СПБТ тыс.т
    df_tabl['SPBT_t_t'] = df_tabl['c3_c4']*df_tabl['Qgas_all']/1e3
    # Оценка объема добычи СПБТ млн.м3
    df_tabl['SPBT_m_m3'] = (comp1 + comp2 + comp3)/100*df_tabl['Qgas_all']
    #
    #
    df_tabl.to_json(r'code_sheets\Base\base_output.json', orient='records', indent=4)
    # === 2 строки × 2 столбца ===
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    # --- График добычи ---
    ax1 = axs[0, 0]
    line1 = ax1.plot(df_tabl['date'], df_tabl['Qgas_all'], color='orange', label="Добыча газа")
    ax1.set_title("График добычи")
    ax1.set_ylabel("Добыча газа, млн. м³")
    ax1.set_xlabel("Дата")
    ax1.grid(True)
    # Создаем вторую ось Y справа
    ax2 = ax1.twinx()
    line2 = ax2.plot(df_tabl['date'], df_tabl['Qcond_all'], color='blue', label="Добыча конденсата")
    ax2.set_ylabel("Добыча конденсата, тыс. т")
    # Получаем линии с обоих графиков
    lines = line1 + line2
    labels = [line.get_label() for line in lines]
    # Создаем одну легенду для всех линий
    ax1.legend(lines, labels, loc='upper right')
    #
    # --- График дебитов ---
    ax2 = axs[0, 1]
    line1 = ax2.plot(df_tabl['date'], df_tabl['debit_gaza_base'], color='orange', label="Дебит газа")
    ax2.set_title("График дебитов")
    ax2.set_ylabel("Дебит газа, тыс.м³/сут")
    ax2.set_xlabel("Дата")
    ax2.grid(True)
    # Создаем вторую ось Y справа
    ax2_1 = ax2.twinx()
    line2 = ax2_1.plot(df_tabl['date'], df_tabl['debit_cond_base_t'], color='blue', label="Дебит конденсата")
    ax2_1.set_ylabel("Дебит конденсата, т/сут")
    # Получаем линии с обоих графиков
    lines = line1 + line2
    labels = [line.get_label() for line in lines]
    # Создаем одну легенду для всех линий
    ax2.legend(lines, labels, loc='upper right')
    #
    # --- График давлений ---
    axs[1, 0].plot(df_tabl['date'], df_tabl['Ppl_mean'], label="Среднее Рпл")
    axs[1, 0].plot(df_tabl['date'], df_tabl['Pzab'], label="Рзаб")
    axs[1, 0].plot(df_tabl['date'], df_tabl['Pust'], label="Ру")
    axs[1, 0].plot(df_tabl['date'], df_tabl['dP'], label="dP")
    axs[1, 0].set_title("График давлений")
    axs[1, 0].set_ylabel("Давление, МПА")
    axs[1, 0].set_xlabel("Дата")
    axs[1, 0].set_ylim(-20, pz_input['P_reservor_init']*1.05)
    axs[1, 0].legend()
    axs[1, 0].grid(True)
    #
    # --- График фонда ---
    axs[1, 1].bar(df_tabl['date'].astype(str), df_tabl['rab_fond_on_end_period'], label="Действующий фонд скважин")
    axs[1, 1].set_title("График фонда скважин")
    axs[1, 1].set_ylabel("Действующий фонд скважин, шт")
    axs[1, 1].set_xlabel("Дата")
    axs[1, 1].legend()
    axs[1, 1].grid(True)
    
    #
    axs[1, 1].xaxis.set_major_locator(ticker.MultipleLocator(12))
    plt.tight_layout()
    #plt.show()
    fig.savefig('code_sheets/Base/base_graph.png', dpi=300, bbox_inches='tight')
    #
    # df_tabl['OIZ_gas_actual'] = oiz_gas - df_tabl['Qgas_all']
    print(df_tabl[['Ppl_on_start_period','Ppl_on_end_period']])
    print(df_tabl[['Qgas_all','Ppl_on_end_period','Qcum_gas_start_period','Qcum_gas_end_period']].iloc[[12,13]])
    print(df_tabl[['Ppl_on_start_period','debit_gaza_base',]].iloc[[12,13]])
    print(df_tabl[['v_zab','v_ust']])
    print(df_tabl[['SPBT_t_t','SPBT_m_m3']])
    print(df_tabl['oiz_cond'])
    #print(df_tabl['oiz_gas'])
if __name__ == "__main__":
    main()