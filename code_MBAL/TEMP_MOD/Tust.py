import math

def Tust(tpl, ge, xi, ldp, t, cp, rc, g, di, pz, pu, l, a, cporod, gem, lm, ldp_m, cporod_m, tm, tcg):
    """Расчет Tust"""
    b = (tm - tcg) ** 2 / (tcg) ** 2
    l1 = l - lm
    temp1 = tpl - ge * l1 + (1 - math.exp(-1 * alfa_1(ldp, t, cp, rc, g, cporod) * l1)) / alfa_1(ldp, t, cp, rc, g, cporod) * (ge - di * (pz - pi(pz, pu, l, l1)) / l1 - a / cp)
    temp2 = temp1 - gem * (xi - l1) + (1 - math.exp(-1 * alfa_1(ldp_m, t, cp, rc, g, cporod_m) * (xi - l1))) / alfa_1(ldp_m, t, cp, rc, g, cporod_m) * (gem - di * (pi(pz, pu, l, l1) - pi(pz, pu, l, xi)) / (xi - l1) - a / cp) * b
    return temp2

def ggas(qg, rg):
    """Расчет массового расхода газа -> кг/ч"""
    return qg * rg * 1000 / 24

def goil(qo, ro):
    """Расчет массового расхода конденсата -> кг/ч"""
    return qo * ro / 24

def gt(gg, go):
    """Расчет массового расхода общий -> кг/ч"""
    return gg + go

def cp(gg, go, cpg, cpo):
    """Расчет Cp"""
    return (gg / (gg + go) * cpg) + (go / (gg + go) * cpo)

def tw(d1, d2):
    """Расчет t"""
    return (d2 - d1) * 24

def pi(pz, pu, l, xi):
    """Расчет Pi"""
    return (pu - pz) * xi / l + pz

def f_1(ldp, t, cp, rc):
    """Вспомогательная функция f_1"""
    return math.log(1 + (math.pi * ldp * t / cp / rc / rc) ** 0.5)

def alfa_1(ldp, t, cp, rc, g, cporod):
    """Расчет alfa_1"""
    f = f_1(ldp, t, cporod, rc)
    return 2 * math.pi * ldp / (g * cp * f)


