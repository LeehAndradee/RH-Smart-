def calcular_inss(salario):
    if salario <= 1412:
        return salario * 0.08
    elif salario <= 2666:
        return salario * 0.09
    else:
        return salario * 0.11


def calcular_irrf(salario):
    if salario <= 2112:
        return 0
    elif salario <= 2826:
        return salario * 0.075
    elif salario <= 3751:
        return salario * 0.15
    else:
        return salario * 0.225


def calcular_fgts(salario):
    return salario * 0.08