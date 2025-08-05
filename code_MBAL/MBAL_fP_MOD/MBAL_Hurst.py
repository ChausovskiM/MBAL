import math

def Mbal_Hurst(Cw, Cf, P, Pi, perm, Time1, poro, visc_w, Re, H, alfa):
    if (perm == 0) or (H == 0) or (Re == 0) or (poro == 0) or (alfa == 0) or (visc_w == 0):
        return 0
    
    tD = 0.00036 * perm * Time1 * 24 / (poro * visc_w * (Cw/10 + Cf/10) * Re**2)
    
    if tD < 0.01:
        WeD = math.sqrt(tD / 3.14)
    elif 0.01 <= tD < 200:
        numerator = (1.2838 * math.sqrt(tD) + 1.19328 * tD + 
                    0.269872 * tD**1.5 + 0.00855294 * tD**2)
        denominator = (1 + 0.616599 * math.sqrt(tD) + 0.0413008 * tD)
        WeD = numerator / denominator
    else:  # tD >= 200
        WeD = (-4.29881 + 2.02566 * tD) / math.log(tD)
    
    u = 0.459 * poro * (Cw/10 + Cf/10) * Re**2 * H * alfa / 360
    return u * (P * 10 - Pi * 10) * WeD / 10**6
