import math

def parse_float(valor, padrao=0.0, minimo=0.0):
    try:
        num = float(str(valor).replace(',', '.'))
        if math.isnan(num) or math.isinf(num) or num < minimo:
            return padrao
        return num
    except (ValueError, TypeError):
        return padrao

def parse_int(valor, padrao=0, minimo=0):
    try:
        num = int(valor)
        return num if num >= minimo else padrao
    except (ValueError, TypeError):
        return padrao

def formata_numero(valor):
    try:
        if valor is None:
            return "0,00"
        return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0,00"