import os
import json
import math
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import datetime
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
from code_MBAL.Complementary_functions.save_figure import save_figure
from code_MBAL.common.paths import runtime_path


GAS_CONTRIBUTION_COLUMNS = [
    'Qgas_vns', 'Qgas_frac', 'Qgas_pvlg', 'Qgas_zbs', 'Qgas_rs',
    'Qgas_vbd', 'Qgas_gtm', 'Qgas_periodic',
]
COND_CONTRIBUTION_COLUMNS = [
    'Qcond_vns', 'Qcond_frac', 'Qcond_pvlg', 'Qcond_zbs', 'Qcond_rs',
    'Qcond_vbd', 'Qcond_gtm', 'Qcond_periodic',
]


def condensate_tonnes_to_m3(tonnes_per_day, density_kgm3):
    """Переводит массовый дебит конденсата, т/сут, в объёмный, м³/сут."""
    if density_kgm3 <= 0:
        raise ValueError("Плотность конденсата должна быть больше нуля")
    return tonnes_per_day * 1000 / density_kgm3


def _ensure_contribution_columns(df_tabl, columns):
    """Сохраняет переданные добычи ГТМ; отсутствующие значения считает нулевыми."""
    for column in columns:
        if column not in df_tabl:
            df_tabl[column] = 0.0
        else:
            df_tabl[column] = pd.to_numeric(df_tabl[column], errors='coerce').fillna(0.0)


def _ensure_numeric_columns(df_tabl, defaults):
    """Сохраняет пользовательский помесячный график и заполняет его пробелы."""
    for column, default in defaults.items():
        if column not in df_tabl:
            df_tabl[column] = default
        else:
            df_tabl[column] = pd.to_numeric(
                df_tabl[column], errors='coerce'
            ).fillna(default)


def _apply_well_schedule(df_tabl, entry_wells):
    """Рассчитывает фонд и отклоняет физически невозможный график скважин."""
    entry_value = float(entry_wells)
    if not math.isfinite(entry_value) or entry_value < 0:
        raise ValueError("Начальный фонд скважин должен быть конечным и неотрицательным")

    df_tabl['rab_fond_on_start_period'] = 0
    df_tabl['rab_fond_on_end_period'] = 0
    current_fund = int(entry_value) if entry_value.is_integer() else entry_value

    for index in df_tabl.index:
        introduced = df_tabl.loc[index, 'vvod_wells_in_curr_period']
        retired = df_tabl.loc[index, 'leave_base_fond']
        retiring_days = float(df_tabl.loc[index, 'time_prod_leaving_wells'])
        period_days = float(df_tabl.loc[index, 'len_report_period'])

        if not all(math.isfinite(float(value)) for value in (
            introduced, retired, retiring_days, period_days
        )):
            raise ValueError(f"График фонда содержит нечисловое значение (строка {index})")
        if introduced < 0 or retired < 0:
            raise ValueError(
                f"Ввод и выбытие скважин не могут быть отрицательными (строка {index})"
            )
        if retiring_days < 0 or retiring_days > period_days:
            raise ValueError(
                f"Время работы выбывающих скважин должно быть от 0 до "
                f"{period_days:g} суток (строка {index})"
            )

        available = current_fund + introduced
        if retired > available:
            raise ValueError(
                f"Нельзя вывести {retired:g} скв. при доступном фонде "
                f"{available:g} скв. (строка {index})"
            )

        df_tabl.loc[index, 'rab_fond_on_start_period'] = current_fund
        current_fund = available - retired
        df_tabl.loc[index, 'rab_fond_on_end_period'] = current_fund

    return df_tabl


def _build_forecast_table(
    table_data, horizon_months, default_exploration_coeff, default_dp_mpa
):
    """Выравнивает пользовательский режим по месяцам, не затирая введённые данные."""
    frame = pd.DataFrame(table_data).copy()
    if 'month' not in frame:
        raise ValueError("В Base.table_data отсутствует колонка month")

    months = pd.to_numeric(frame['month'], errors='coerce')
    if months.isna().any() or (months % 1 != 0).any():
        raise ValueError("Номера месяцев должны быть целыми числами")
    frame['month'] = months.astype(int)
    if frame['month'].duplicated().any():
        raise ValueError("В Base.table_data есть повторяющиеся месяцы")
    if not frame['month'].between(1, horizon_months).all():
        raise ValueError(f"Номер месяца должен быть от 1 до {horizon_months}")

    frame = frame.set_index('month').reindex(range(1, horizon_months + 1))
    frame.index.name = 'month'
    for column, default in {
        'exploration_coeff': default_exploration_coeff,
        'dP': default_dp_mpa,
    }.items():
        if column not in frame:
            frame[column] = default
            continue
        values = pd.to_numeric(frame[column], errors='coerce')
        invalid = frame[column].notna() & values.isna()
        if invalid.any():
            raise ValueError(f"Колонка {column} содержит нечисловое значение")
        frame[column] = values.fillna(default)

    if not frame['exploration_coeff'].between(0, 1).all():
        raise ValueError("Коэффициент эксплуатации должен быть от 0 до 1")
    if (frame['dP'] < 0).any():
        raise ValueError("Депрессия не может быть отрицательной")
    return frame.reset_index()


def _calculate_base_wellhead_pressure(
    pzab, qgas, base_input, pvt_input, pvt_output, pz_input
):
    """Считает Ру с MD для трения и TVD для гидростатического столба."""
    return Pust(
        pzab, qgas, base_input['d_nkt'], base_input['pipe_absolute_roughness'],
        pvt_output['gas_relative_density'],
        base_input.get('well_md', base_input['well_tvd']), base_input['T_ust'],
        pz_input['T_reservor_init'], pvt_input['Z_method'],
        base_input['viscosity_method'], pvt_input['density_method'],
        base_input['hydraulic_resistance_method'],
        base_input['hydraulic_resistance_coefficient'], base_input['well_tvd'],
    )


def _operating_limit_reason(qgas, pzab, pvt_input, pvt_output, pz_input, base_input):
    """Возвращает причину остановки скважины или пустую строку."""
    pust = _calculate_base_wellhead_pressure(
        pzab, qgas, base_input, pvt_input, pvt_output, pz_input
    )
    vmin_tochigin = Tochigin(
        pzab, pz_input['T_reservor_init'], base_input['sigm_water'],
        base_input['condensate_density_kgm3'], base_input['d_nkt'],
        pvt_input['Z_method'], pvt_input['density_method'], pvt_output['gas_relative_density'],
    )
    v_zab = Velosity(
        pvt_input['Z_method'], pz_input['T_reservor_init'], qgas, pzab, base_input['d_nkt']
    )
    v_ust = Velosity(
        pvt_input['Z_method'], base_input['T_ust'], qgas, pust, base_input['d_nkt']
    )

    if pust < base_input.get('min_wellhead_pressure_mpa', 5.0):
        return 'минимальное устьевое давление'
    min_bottom_velocity = max(
        base_input.get('min_bottomhole_velocity_ms', 1.5), vmin_tochigin
    )
    if v_zab < min_bottom_velocity:
        return 'минимальная скорость выноса жидкости'
    if v_ust > base_input.get('max_wellhead_velocity_ms', 26.0):
        return 'максимальная скорость на устье'
    return ''


def _validate_base_operation(
    row, pvt_input, pvt_output, pz_input, base_input, previous_row=None
):
    """Применяет ограничения Excel к рассчитанному режиму базовой скважины."""
    ppl = float(row['Ppl_on_start_period'])
    drawdown = float(row['dP'])
    pzab = float(row['Pzab'])
    debit = float(row['debit_gaza_base'])

    if (
        previous_row is not None
        and previous_row.get('operation_status') == 'остановлена'
        and previous_row.get('operation_limit') != 'нет действующего фонда'
        and not base_input.get('restart_stopped_wells', False)
    ):
        return (
            max(ppl, 0.0), 0.0, 0.0, 'остановлена',
            previous_row.get('operation_limit', 'остановлена ранее'),
        )

    if row['mean_rab_basefond'] <= 0:
        reason = 'нет действующего фонда'
    elif ppl <= 0:
        reason = 'неположительное пластовое давление'
    elif drawdown <= 0:
        reason = 'нет депрессии'
    elif drawdown > base_input.get('max_depression_mpa', 10.0):
        reason = 'максимальная депрессия'
    elif ppl - drawdown <= 0:
        reason = 'неположительное забойное давление'
    elif debit <= 0:
        reason = 'нет притока'
    elif base_input.get('enforce_operating_limits', True):
        reason = _operating_limit_reason(
            debit, pzab, pvt_input, pvt_output, pz_input, base_input
        )
    else:
        reason = ''

    if reason:
        return max(ppl, 0.0), 0.0, 0.0, 'остановлена', reason
    return pzab, float(row['lmbda']), debit, 'работает', ''


# Функция для определения количества дней в месяце
def days_in_month(date):
    year = date.year
    month = date.month
    return monthrange(year, month)[1]

def main():
    # инпуты листа PVT
    with runtime_path("code_sheets", "PVT", "pvt_input.json").open('r', encoding='utf-8') as f:
        pvt_input = json.load(f) 
    # Оутпут листа PVT
    with runtime_path("code_sheets", "PVT", "pvt_output.json").open('r', encoding='utf-8') as f:
        pvt_output = json.load(f)    
    # инпуты листа PZ
    with runtime_path("code_sheets", "PZ", "pz_input.json").open('r', encoding='utf-8') as f:
        pz_input = json.load(f)
    start_dev_date = pz_input["start_dev_date"]
    start_predcit_date = pz_input["start_predict_date"]
    #
    # Инпуты листа БАЗА
    with runtime_path("code_sheets", "Base", "base_input.json").open('r', encoding='utf-8') as f:
        base_input = json.load(f)
    df_tabl = _build_forecast_table(
        base_input["table_data"], 1200,
        base_input["default_exploration_coeff"],
        base_input.get("default_dP_mpa", 2.6),
    )
    # Оутпуты листа Продуктивность
    with runtime_path("code_sheets", "Productivity", "productivity_output.json").open('r', encoding='utf-8') as f:
        product_outputs_df = pd.DataFrame(json.load(f)["results_table"])
    #
    # определяем 1) Давление начала конденсации 2) Начальный КГФ
    if base_input['kgf_method'] == "experimental data":
        # Инпуты листа КГФ - ЭКСПЕРИМЕНТАЛЬНАЯ ЗАВИСИМОСТЬ
        with runtime_path("code_sheets", "KGF", "kgf_experimental_input.json").open(encoding="utf-8") as f:
            kgf_exp_input = json.load(f)
        Pnk, kgf = kgf_exp_input['Pnk'], kgf_exp_input['Pnk']
        # Оутпут листа КГФ
        with runtime_path("code_sheets", "KGF", "kgf_output.json").open(encoding="utf-8") as f:
            kgf_output = json.load(f)
        kgf = kgf_output['C5_plus']
    elif base_input['kgf_method'] == "typical dependence": 
        # Инпуты листа КГФ - ТИПОВАЯ ЗАВИСИМОСТЬ
        with runtime_path("code_sheets", "KGF", "kgf_typical_input.json").open(encoding="utf-8") as f:
            kgf_type_input = json.load(f)
            Pnk, kgf = kgf_type_input['Pnk'], kgf_type_input['KGF'] 
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
    # График движения фонда задаётся пользователем, как и в исходной книге.
    # Если колонок нет, сохраняется прежнее поведение с нулевыми значениями.
    _ensure_numeric_columns(df_tabl, {
        'leave_base_fond': 0,
        'time_prod_leaving_wells': 0,
        'vvod_wells_in_curr_period': 0,
    })
    #
    # Действующий базовый фонд на начало/конец периода.
    df_tabl = _apply_well_schedule(df_tabl, base_input['entry_wells'])

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
    # Сохраняем переданные добычи ГТМ; отсутствующие колонки считаем нулевыми.
    _ensure_contribution_columns(df_tabl, GAS_CONTRIBUTION_COLUMNS)
    _ensure_contribution_columns(df_tabl, COND_CONTRIBUTION_COLUMNS)
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
            df_tabl.loc[i,'Pzab'] = max(
                df_tabl.loc[i,'Ppl_on_start_period'] - df_tabl.loc[i,'dP'], 0.0
            )
            # 
            # расчет лямбды через ld
            df_tabl.loc[i,'lmbda'] = (
                Ld(pvt_input["Z_method"], pvt_input["density_method"], base_input["viscosity_method"],(df_tabl.loc[i,'Ppl_on_start_period']+df_tabl.loc[i,'Pzab'])/2, pz_input['T_reservor_init'])
                if df_tabl.loc[i,'Pzab'] > 0 else 0.0
            )
            # Дебит газа базовых скважин
            if df_tabl.loc[i, 'mean_rab_basefond'] > 0:
                if base_input["qgas_method"] == 'типовая зависимость':
                    df_tabl.loc[i, 'debit_gaza_base'] = fQ(df_tabl.loc[i, 'A'], df_tabl.loc[i, 'B'], df_tabl.loc[i, 'Ppl_on_start_period'], df_tabl.loc[i, 'Pzab'])
                else:
                    df_tabl.loc[i, 'debit_gaza_base'] = fQLd(df_tabl.loc[i, 'A'], df_tabl.loc[i, 'B'], df_tabl.loc[i, 'lmbda'],df_tabl.loc[i, 'Ppl_on_start_period'], df_tabl.loc[i, 'Pzab'])
            else:
                df_tabl.loc[i, 'debit_gaza_base'] = 0
            (df_tabl.loc[i,'Pzab'], df_tabl.loc[i,'lmbda'],
             df_tabl.loc[i,'debit_gaza_base'], df_tabl.loc[i,'operation_status'],
             df_tabl.loc[i,'operation_limit']) = _validate_base_operation(
                df_tabl.loc[i], pvt_input, pvt_output, pz_input, base_input
            )
            #
            # Добыча газа из базовых скважин
            df_tabl.loc[i,'Qgas_base_fond'] = df_tabl.loc[i,['len_report_period','mean_rab_basefond','debit_gaza_base']].prod()/1000
            #
            # Добыча газа всего
            df_tabl.loc[i,'Qgas_all'] = df_tabl.loc[i,['Qgas_base_fond', *GAS_CONTRIBUTION_COLUMNS]].sum()
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
            df_tabl.loc[i,'Pzab'] = max(
                df_tabl.loc[i,'Ppl_on_start_period'] - df_tabl.loc[i,'dP'], 0.0
            )
            df_tabl.loc[i,'lmbda'] = (
                Ld(pvt_input["Z_method"], pvt_input["density_method"], base_input["viscosity_method"],(df_tabl.loc[i,'Ppl_on_start_period']+df_tabl.loc[i,'Pzab'])/2, pz_input['T_reservor_init'])
                if df_tabl.loc[i,'Pzab'] > 0 else 0.0
            )
             # Дебит газа базовых скважин
            if df_tabl.loc[i, 'mean_rab_basefond'] > 0:
                if base_input["qgas_method"] == 'типовая зависимость':
                    df_tabl.loc[i, 'debit_gaza_base'] = fQ(df_tabl.loc[i, 'A'], df_tabl.loc[i, 'B'], df_tabl.loc[i, 'Ppl_on_start_period'], df_tabl.loc[i, 'Pzab'])
                else:
                    df_tabl.loc[i, 'debit_gaza_base'] = fQLd(df_tabl.loc[i, 'A'], df_tabl.loc[i, 'B'], df_tabl.loc[i, 'lmbda'],df_tabl.loc[i, 'Ppl_on_start_period'], df_tabl.loc[i, 'Pzab'])
            else:
                df_tabl.loc[i, 'debit_gaza_base'] = 0
            (df_tabl.loc[i,'Pzab'], df_tabl.loc[i,'lmbda'],
             df_tabl.loc[i,'debit_gaza_base'], df_tabl.loc[i,'operation_status'],
             df_tabl.loc[i,'operation_limit']) = _validate_base_operation(
                df_tabl.loc[i], pvt_input, pvt_output, pz_input, base_input,
                previous_row=df_tabl.loc[i-1],
            )
            df_tabl.loc[i,'Qgas_base_fond'] = df_tabl.loc[i,['len_report_period','mean_rab_basefond','debit_gaza_base']].prod()/1000
            df_tabl.loc[i,'Qgas_all'] = df_tabl.loc[i,['Qgas_base_fond', *GAS_CONTRIBUTION_COLUMNS]].sum()
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
    # Дебит конденсата базовых скважин т/сут
    df_tabl['debit_cond_base_t'] = df_tabl['debit_gaza_base']*df_tabl['KGF']/1000
    #
    # Дебит конденсата базовых скважин м3/сут
    df_tabl['debit_cond_base_m3'] = df_tabl['debit_cond_base_t'].apply(
        lambda value: condensate_tonnes_to_m3(value, base_input['condensate_density_kgm3'])
    )
    #
    # Добыча конденсата из базовых скважин тыс.т
    df_tabl['Qcond_base_fond'] = df_tabl[['len_report_period','mean_rab_basefond','debit_cond_base_t']].prod(axis=1)/1000
    #
    # Добыча конденсата всего тыс т
    df_tabl['Qcond_all'] = df_tabl[['Qcond_base_fond', *COND_CONTRIBUTION_COLUMNS]].sum(axis=1)
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
    df_tabl['Pust'] = df_tabl.apply(
        lambda row: _calculate_base_wellhead_pressure(
            row['Pzab'], row['debit_gaza_base'], base_input,
            pvt_input, pvt_output, pz_input,
        ),
        axis=1,
    )
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
    with runtime_path("code_sheets", "PVT", "gas_components.json").open(encoding="utf-8") as f:
        gas_components = pd.DataFrame(json.load(f))
    # E11,E12,E13 с листа PVT
    Mw_propan = gas_components[gas_components['formula']=='C3H8']['Mw'].values[0]
    Mw_izobutan = gas_components[gas_components['formula']=='i-C4H10']['Mw'].values[0]
    Mw_nbutan = gas_components[gas_components['formula']=='n-C4H10']['Mw'].values[0]
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
    df_tabl.to_json(
        runtime_path('code_sheets', 'Base', 'base_output.json'),
        orient='records', indent=4,
    )
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
    save_figure(
        fig, runtime_path('code_sheets', 'Base', 'base_graph.png'),
        dpi=300, bbox_inches='tight',
    )
    plt.close(fig)
    #
    # df_tabl['OIZ_gas_actual'] = oiz_gas - df_tabl['Qgas_all']
    #print(df_tabl['oiz_gas'])
if __name__ == "__main__":
    main()
