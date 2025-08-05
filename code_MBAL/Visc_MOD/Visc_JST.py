import math

def Density(Mw_mix,P_Mpa,T_C_plast,Z_calc):
    rho0 = Mw_mix / 24.04  # нормальная плотность, кг/м³
    rho = rho0 * P_Mpa*10**6 * 293.15 / (101325 * (T_C_plast+273.15) * Z_calc) #строка 12
    return rho

import math

def Visc_JST(P_MPA, T_C, Z, XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange):
    """
    Расчет вязкости по корреляции Jossi, Stiel, Thodos
    Точный аналог VBA-функции с учетом особенностей Python
    """
    
    # Константы для оценки вязкости (как в VBA)
    A1 = 0.1023
    A2 = 0.023364
    A3 = 0.058533
    A4 = -0.040758
    A5 = 0.0093324
    
    # Преобразование единиц (как в VBA)
    P_Pa = P_MPA * 10**6  # МПа -> Па
    T_K = T_C + 273.15    # °C -> K
    
    # Инициализация переменных (как в VBA)
    visc_up = 0.0
    visc_down = 0.0
    tkr = 0.0
    Pkr = 0.0
    Vkr = 0.0
    Zkr = 0.0
    m = 0.0
    
    # Расчет псевдокритических параметров (точный аналог VBA-цикла)
    for i in range(12):
        Xi = XiRange.iloc[i] / 100  # Мольная доля (перевод из %)
        Mi = MwRange.iloc[i]        # Молекулярная масса
        Tkri = TcRange.iloc[i]       # Критическая температура
        Pkri = PcRange.iloc[i] * 10**6  # Критическое давление (перевод в Па)
        Vkri = VcRange.iloc[i]       # Критический объем
        Zkri = ZcRange.iloc[i]       # Критический коэффициент сжимаемости
        
        # Расчет псевдокритических параметров (правило аддитивности)
        tkr += Tkri * Xi
        Pkr += Pkri * Xi
        Vkr += Vkri * Xi
        Zkr += Zkri * Xi
        m += Mi * Xi
        
        # Расчет корреляционного коэффициента (как в VBA)
        Ei = 0.0
        if Mi != 0 and Pkri != 0:
            Ei = Tkri**(1/6) * Mi**(-1/2) * (Pkri/10**5)**(-2/3)
        
        # Приведенная температура для компонента
        Tpri = 0.0
        if Tkri != 0:
            Tpri = T_K / Tkri
        
        # Расчет вязкости для компонента (как в VBA)
        visci = 0.0
        if Tkri != 0:
            if Tpri <= 1.5:
                if Ei != 0:
                    visci = 34 * 10**-5 * Tpri**(8/9) / Ei * 1000
            else:
                if Ei != 0:
                    visci = 166.8 * 10**-5 * (0.1338 * Tpri - 0.0932)**(5/9) / Ei * 1000
        
        # Вспомогательные коэффициенты (как в VBA)
        visc_up += Xi * visci * math.sqrt(Mi)
        visc_down += Xi * math.sqrt(Mi)
    
    # Корреляционный коэффициент для смеси (как в VBA)
    e = tkr**(1/6) * m**(-1/2) * (Pkr/10**5)**(-2/3)
    
    # Вязкость при атмосферном давлении (как в VBA)
    visc0 = visc_up / visc_down if visc_down != 0 else 0.0
    
    # Расчет приведенной плотности (с учетом ваших уточнений)
    rho = Density(m, P_MPA, T_C, Z)          # Текущая плотность
    rho_cr = Density(m, Pkr/10**6, tkr-273.15, Zkr)  # Критическая плотность
    
    Dpr = rho / rho_cr if rho_cr != 0 else 0.0
    Tpr = T_K / tkr if tkr != 0 else 0.0
    
    # Финальный расчет вязкости (как в VBA)
    term = A1 + A2*Dpr + A3*Dpr**2 + A4*Dpr**3 + A5*Dpr**4
    viscosity = ((term**4 - 10**-4) / e * 1000 + visc0) if e != 0 else visc0
    
    return viscosity

# print(Density(17.9,20.966,59.50,0.849))