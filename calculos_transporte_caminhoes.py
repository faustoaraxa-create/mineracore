from flask import Blueprint, render_template, request, session
import math
from utils import parse_float, formata_numero

caminhoes_bp = Blueprint('caminhoes', __name__)

def calcular_dimensionamento_caminhoes(dados_banco, dados_carga, modelo_caminhao, 
                                        capacidade_caminhao_t, distancia_ida_km, 
                                        distancia_volta_km, vel_carregado_kmh, 
                                        vel_vazio_kmh, tempo_manobra_praca_min, 
                                        tempo_basculamento_min, eficiencia_transporte):
    vol_solto_total = dados_banco.get('volume_solto_raw', 0.0)
    tonelagem_total = dados_banco.get('tonelagem_raw', 0.0)
    densidade_solta = (tonelagem_total / vol_solto_total) if vol_solto_total > 0 else 1.60

    capacidade_concha_m3 = dados_carga.get('capacidade_concha', 15.0)
    fator_enchimento = dados_carga.get('fator_enchimento', 85.0) / 100.0
    tempo_ciclo_escavadeira_s = parse_float(dados_carga.get('tempo_ciclo_segundos'), padrao=32.0, minimo=1.0)
    eficiencia_escavadeira = parse_float(dados_carga.get('eficiencia_operador'), padrao=85.0, minimo=1.0) / 100.0

    tipo_coroamento = dados_carga.get('tipo_coroamento', 'heaped_2_1')
    fatores_coroamento = {'struck': 0.88, 'heaped_2_1': 1.00, 'heaped_1_1': 1.08}
    fator_coroamento = fatores_coroamento.get(tipo_coroamento, 1.00)

    carga_efetiva_concha_t = capacidade_concha_m3 * fator_coroamento * fator_enchimento * densidade_solta

    passadas = max(1, round(capacidade_caminhao_t / carga_efetiva_concha_t)) if carga_efetiva_concha_t > 0 else 1
    carga_real_caminhao_t = passadas * carga_efetiva_concha_t
    volume_cacamba_m3 = carga_real_caminhao_t / densidade_solta if densidade_solta > 0 else 0.0

    tempo_carga_min = (passadas * tempo_ciclo_escavadeira_s) / 60.0
    tempo_ida_min = (distancia_ida_km / vel_carregado_kmh) * 60.0 if vel_carregado_kmh > 0 else 0.0
    tempo_volta_min = (distancia_volta_km / vel_vazio_kmh) * 60.0 if vel_vazio_kmh > 0 else 0.0

    tempo_ciclo_bruto_min = (tempo_carga_min + tempo_ida_min + tempo_basculamento_min + 
                             tempo_volta_min + tempo_manobra_praca_min)
    
    eficiencia_fator = (eficiencia_transporte / 100.0) if eficiencia_transporte > 0 else 1.0
    tempo_ciclo_caminhao_min = tempo_ciclo_bruto_min / eficiencia_fator

    numero_caminhoes_teorico = tempo_ciclo_caminhao_min / tempo_carga_min if tempo_carga_min > 0 else 1.0
    caminhoes_sem_fila = max(1, math.floor(numero_caminhoes_teorico))
    caminhoes_escavadeira_100 = math.ceil(numero_caminhoes_teorico)
    caminhoes_por_hora_real = (60.0 * eficiencia_escavadeira) / tempo_carga_min if tempo_carga_min > 0 else 0.0

    return {
        'modelo_caminhao': modelo_caminhao,
        'capacidade_caminhao_t': capacidade_caminhao_t,
        'volume_cacamba_m3_formatado': formata_numero(volume_cacamba_m3),
        'distancia_ida_km': distancia_ida_km,
        'distancia_volta_km': distancia_volta_km,
        'vel_carregado_kmh': vel_carregado_kmh,
        'vel_vazio_kmh': vel_vazio_kmh,
        'tempo_manobra_praca_min': tempo_manobra_praca_min,
        'tempo_basculamento_min': tempo_basculamento_min,
        'eficiencia_transporte': eficiencia_transporte,
        'passadas': passadas,
        'carga_real_caminhao_t': formata_numero(carga_real_caminhao_t),
        'tempo_carga_min': formata_numero(tempo_carga_min),
        'tempo_ciclo_caminhao_min': formata_numero(tempo_ciclo_caminhao_min),
        'numero_caminhoes_teorico': formata_numero(numero_caminhoes_teorico),
        'caminhoes_sem_fila': caminhoes_sem_fila,
        'caminhoes_escavadeira_100': caminhoes_escavadeira_100,
        'caminhoes_por_hora_real': formata_numero(caminhoes_por_hora_real)
    }

@caminhoes_bp.route('/dimensionamento_caminhoes', methods=['GET', 'POST'])
def caminhoes():
    dados_banco = session.get('dados_banco')
    dados_carga = session.get('dados_carga')

    if request.method == 'POST':
        if not dados_banco or not dados_carga:
            return render_template('dimensionamento_caminhoes.html', dados=None)

        modelo_caminhao = request.form.get('modelo_caminhao', 'Caterpillar 777F').strip()[:100]
        capacidade_caminhao_t = parse_float(request.form.get('capacidade_caminhao_t'), padrao=100.0, minimo=1.0)
        distancia_ida_km = parse_float(request.form.get('distancia_ida_km'), padrao=2.5, minimo=0.0)
        distancia_volta_km = parse_float(request.form.get('distancia_volta_km'), padrao=2.5, minimo=0.0)
        vel_carregado_kmh = parse_float(request.form.get('vel_carregado_kmh'), padrao=22.0, minimo=1.0)
        vel_vazio_kmh = parse_float(request.form.get('vel_vazio_kmh'), padrao=35.0, minimo=1.0)
        tempo_manobra_praca_min = parse_float(request.form.get('tempo_manobra_praca_min'), padrao=1.0, minimo=0.0)
        tempo_basculamento_min = parse_float(request.form.get('tempo_basculamento_min'), padrao=1.5, minimo=0.0)
        eficiencia_transporte = parse_float(request.form.get('eficiencia_transporte'), padrao=85.0, minimo=1.0)

        resultado = calcular_dimensionamento_caminhoes(
            dados_banco=dados_banco,
            dados_carga=dados_carga,
            modelo_caminhao=modelo_caminhao,
            capacidade_caminhao_t=capacidade_caminhao_t,
            distancia_ida_km=distancia_ida_km,
            distancia_volta_km=distancia_volta_km,
            vel_carregado_kmh=vel_carregado_kmh,
            vel_vazio_kmh=vel_vazio_kmh,
            tempo_manobra_praca_min=tempo_manobra_praca_min,
            tempo_basculamento_min=tempo_basculamento_min,
            eficiencia_transporte=eficiencia_transporte
        )

        session['dados_transporte'] = resultado
        return render_template('dimensionamento_caminhoes.html', dados=resultado)

    return render_template('dimensionamento_caminhoes.html', dados=None)