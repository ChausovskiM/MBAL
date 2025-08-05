# from code_MBAL.MBAL_fP_MOD.Mbal_Hurst import Mbal_Hurst
# from code_MBAL.MBAL_fP_MOD.Mbal_P import Mbal_P
#
from code_MBAL.Z_MOD.Z_calc import Z_calc

from code_MBAL.MBAL_fP_MOD.MBAL_Hurst import Mbal_Hurst
#
import math
import pandas as pd
import json

def MBAL_fP(Pn, Tn, Zn, G, Gp, Cf, Cw, k, m, R, H, Tj, alfa, visc_w, Swi, ZCOR):
    # Конвертация единиц
    Cf = Cf / 1000
    Cw = Cw / 1000
    
    # Стандартные параметры для Mbal_B
    Tst = 20  # стандартная температура, °C
    Pst = 0.101325  # стандартное давление, МПа
        
    Pxa = Pn
    b = Pst * (0 + 273.15) / (Tst + 273.15)  # t=0 передается как аргумент
    
    Zj = Z_calc(ZCOR, Pxa, Tn)
    if (k == 0) or (H == 0) or (R == 0) or (m == 0) or (alfa == 0) or (visc_w == 0):
        We = 0
    else:
        We = Mbal_Hurst(Cw, Cf, Pn, Pxa, k, Tj, m, visc_w, R, H, alfa)
    
    # Встроенный расчет Mbal_C, Mbal_D, Mbal_E для f_a
    A_val = (Cf + Cw * Swi) / (1 - Swi)
    C_val = Zn / Pn - Zn * A_val - We / G / (Pst * (Tn + 273.15) / (Tst + 273.15))
    D_val = -Zn * A_val / Pn
    E_val = (1 - Gp / G) * Zj
    
    f_a = (C_val - math.sqrt(C_val**2 - 4 * D_val * E_val)) / (2 * D_val) - Pxa if (C_val**2 - 4 * D_val * E_val) >= 0 else -Pxa
    
    Pxb = 0.1
    Zj = Z_calc(ZCOR, Pxb, Tn)
    if (k == 0) or (H == 0) or (R == 0) or (m == 0) or (alfa == 0) or (visc_w == 0):
        We = 0
    else:
        We = Mbal_Hurst(Cw, Cf, Pn, Pxb, k, Tj, m, visc_w, R, H, alfa)
    
    # Повторный расчет для f_b
    A_val = (Cf + Cw * Swi) / (1 - Swi)
    C_val = Zn / Pn - Zn * A_val - We / G / (Pst * (Tn + 273.15) / (Tst + 273.15))
    D_val = -Zn * A_val / Pn
    E_val = (1 - Gp / G) * Zj
    
    f_b = (C_val - math.sqrt(C_val**2 - 4 * D_val * E_val)) / (2 * D_val) - Pxb if (C_val**2 - 4 * D_val * E_val) >= 0 else -Pxb
    
    Pxa = Pxa + ((Pxa - Pxb) * f_a) / (f_b - f_a)
    
    for i in range(6):
        Pxa1 = Pxa
        b = Pst * (0 + 273.15) / (Tst + 273.15)
        Zj = Z_calc(ZCOR, Pxa, Tn)
        
        if (k == 0) or (H == 0) or (R == 0) or (m == 0) or (alfa == 0) or (visc_w == 0):
            We = 0
        else:
            We = Mbal_Hurst(Cw, Cf, Pn, Pxa, k, Tj, m, visc_w, R, H, alfa)
        
        # Расчет для текущей итерации
        A_val = (Cf + Cw * Swi) / (1 - Swi)
        C_val = Zn / Pn - Zn * A_val - We / G / (Pst * (Tn + 273.15) / (Tst + 273.15))
        D_val = -Zn * A_val / Pn
        E_val = (1 - Gp / G) * Zj
        
        f_a = (C_val - math.sqrt(C_val**2 - 4 * D_val * E_val)) / (2 * D_val) - Pxa if (C_val**2 - 4 * D_val * E_val) >= 0 else -Pxa
        
        Pxa = Pxa - ((Pxb - Pxa) * f_a) / (f_b - f_a)
        
        if f_a > 0:
            f_b = f_a
            Pxb = Pxa1
        
        if round(f_a, 2) == 0:
            break
    
    return Pxa

