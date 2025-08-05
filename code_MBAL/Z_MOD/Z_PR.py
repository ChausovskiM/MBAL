import numpy as np
import pandas as pd
from math import acos, cos, sqrt, copysign

def Z_PR(P_MPA: float, T_C: float, 
         XiRange: pd.Series, MwRange: pd.Series, TcRange: pd.Series, 
         PcRange: pd.Series, VcRange: pd.Series, ZcRange: pd.Series, 
         wRange: pd.Series) -> float:
    """
    Расчет коэффициента сверхсжимаемости по уравнению состояния Пенга-Робинсона
    
    Parameters:
    P_MPA - давление, МПа
    T_C - температура, °C
    XiRange, MwRange, TcRange, PcRange, VcRange, ZcRange, wRange - pd.Series с параметрами компонентов
    
    Returns:
    Z1 - коэффициент сверхсжимаемости
    """
    
    # Перевод единиц измерения
    P_Pa = P_MPA * 10**6  # Па
    T_K = T_C + 273.15    # К
    R = 287               # Дж/(К*моль)
    
    # Расчет коэффициентов
    A = A_PR(P_Pa, T_K, XiRange, TcRange, PcRange, wRange)
    b = B_PR(P_Pa, T_K, XiRange, TcRange, PcRange)
    
    # Коэффициенты для уравнения состояния Пенга-Робинсона
    m1 = 1 + sqrt(2)
    m2 = 1 - sqrt(2)
    
    # Вспомогательные коэффициенты
    E0 = - (A * b + m1 * m2 * b**2 * (b + 1))
    E1 = A - (2 * (m1 + m2) - 1) * b**2 - (m1 + m2) * b
    E2 = (m1 + m2 - 1) * b - 1
    
    # Решение кубического уравнения методом Хорд
    Qv = (E2**2 - 3 * E1) / 9
    Rv = (2 * E2**3 - 9 * E2 * E1 + 27 * E0) / 54
    
    if Rv**2 < Qv**3:
        Tv = acos(Rv / Qv**(3/2)) / 3
        Z1 = -2 * sqrt(Qv) * cos(Tv) - E2 / 3
        Z2 = -2 * sqrt(Qv) * cos(Tv + (2 * np.pi / 3)) - E2 / 3
        Z3 = -2 * sqrt(Qv) * cos(Tv - (2 * np.pi / 3)) - E2 / 3
    else:
        AA = -copysign(1, Rv) * (abs(Rv) + sqrt(Rv**2 - Qv**3))**(1/3)
        BB = Qv / AA
        
        Z1 = (AA + BB) - E2 / 3
        
        if AA == BB:
            Z2 = -AA - E2 / 3
            Z3 = Z2
        else:
            Z2 = -(AA + BB) / 2 - E2 / 3 + sqrt(3) * (AA - BB)
            Z3 = -(AA + BB) / 2 - E2 / 3 - sqrt(3) * (AA - BB)
    
    return Z1

def A_PR(P: float, T: float, 
         XiRange: pd.Series, TcRange: pd.Series, 
         PcRange: pd.Series, wRange: pd.Series) -> float:
    """
    Расчет коэффициента A для уравнения состояния PR
    
    Parameters:
    P - давление, Па
    T - температура, К
    XiRange, TcRange, PcRange, wRange - pd.Series с параметрами компонентов
    
    Returns:
    A - коэффициент A
    """
    A = 0.0
    n = len(XiRange)
    
    for i in range(n):
        for j in range(n):
            Xi = XiRange.iloc[i] / 100
            Xj = XiRange.iloc[j] / 100
            A += Xi * Xj * Aij_PR(P, T, i, j, XiRange, TcRange, PcRange, wRange)
    
    return A

def B_PR(P: float, T: float, 
         XiRange: pd.Series, TcRange: pd.Series, 
         PcRange: pd.Series) -> float:
    """
    Расчет коэффициента B для уравнения состояния PR
    
    Parameters:
    P - давление, Па
    T - температура, К
    XiRange, TcRange, PcRange - pd.Series с параметрами компонентов
    
    Returns:
    B - коэффициент B
    """
    B = 0.0
    n = len(XiRange)
    
    for i in range(n):
        Xi = XiRange.iloc[i] / 100
        B += Bi_PR(P, T, i, TcRange, PcRange) * Xi
    
    return B

def Ai_PR(P: float, T: float, i: int, 
          TcRange: pd.Series, PcRange: pd.Series, 
          wRange: pd.Series) -> float:
    """
    Расчет коэффициента Ai для уравнения состояния PR
    
    Parameters:
    P - давление, Па
    T - температура, К
    i - индекс компонента
    TcRange, PcRange, wRange - pd.Series с параметрами компонентов
    
    Returns:
    Ai - коэффициент Ai
    """
    Pkr = PcRange.iloc[i] * 10**6  # Па
    Tkr = TcRange.iloc[i]          # K
    w = wRange.iloc[i]
    
    if Pkr == 0 or Tkr == 0:
        return 0.0
    
    Ppr = P / Pkr
    Tpr = T / Tkr
    
    return 0.457235529 * (1 + (0.37464 + 1.54226 * w - 0.2669 * w**2) * 
                         (1 - sqrt(Tpr)))**2 * Ppr / Tpr**2

def Bi_PR(P: float, T: float, i: int, 
          TcRange: pd.Series, PcRange: pd.Series) -> float:
    """
    Расчет коэффициента Bi для уравнения состояния PR
    
    Parameters:
    P - давление, Па
    T - температура, К
    i - индекс компонента
    TcRange, PcRange - pd.Series с параметрами компонентов
    
    Returns:
    Bi - коэффициент Bi
    """
    Pkr = PcRange.iloc[i] * 10**6  # Па
    Tkr = TcRange.iloc[i]          # K
    
    if Tkr == 0:
        return 0.0
    
    Ppr = P / Pkr if Pkr != 0 else 0.0
    Tpr = T / Tkr
    
    return 0.077796074 * Ppr / Tpr

def Aij_PR(P: float, T: float, i: int, j: int, 
           XiRange: pd.Series, TcRange: pd.Series, 
           PcRange: pd.Series, wRange: pd.Series) -> float:
    """
    Расчет коэффициента Aij для уравнения состояния PR
    
    Parameters:
    P - давление, Па
    T - температура, К
    i, j - индексы компонентов
    XiRange, TcRange, PcRange, wRange - pd.Series с параметрами компонентов
    
    Returns:
    Aij - коэффициент Aij
    """
    return (1 - kij(i, j)) * sqrt(Ai_PR(P, T, i, TcRange, PcRange, wRange) * 
                             Ai_PR(P, T, j, TcRange, PcRange, wRange))

def kij(i: int, j: int) -> float:
    """
    Коэффициент бинарного взаимодействия
    
    Parameters:
    i, j - индексы компонентов
    
    Returns:
    kij - коэффициент бинарного взаимодействия
    """
    # Здесь должна быть реализация расчета kij
    # В оригинальном коде она не показана, поэтому возвращаем 0
    return 0.0