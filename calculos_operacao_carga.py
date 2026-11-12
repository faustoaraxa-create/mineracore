from flask import Blueprint, render_template, request, session
from utils import parse_float, parse_int, formata_numero

operacao_bp = Blueprint('operacao', __name__)

# ==============================================================================
# LÓGICA MATEMÁTICA DE ENGENHARIA DE CARGA (ESCAVADEIRA / CARREGADEIRA)
# ==============================================================================
def calcular_operacao_carga(volume_solto_total, tonelagem_total, capacidade_concha, 
                            tipo_coroamento, fator_enchimento, tempo_ciclo_segundos, 
                            angulo_giro, eficiencia_operador, horas_trabalho_dia):
    fatores_coroamento = {
        'struck': 0.88,
        'heaped_2_1': 1.00,
        'heaped_1_1': 1.08
    }
    fator_coroamento = fatores_coroamento.get(tipo_coroamento, 1.00)

    fatores_giro = {
        60: 0.91,
        90: 1.00,
        120: 1.09,
        180: 1.20
    }
    fator_giro = fatores_giro.get(int(angulo_giro), 1.00)

    tempo_ciclo_corrigido = tempo_ciclo_segundos * fator_giro
    volume_passada = capacidade_concha * fator_coroamento * (fator_enchimento / 100.0)
    ciclos_por_hora_teorico = 3600.0 / tempo_ciclo_corrigido if tempo_ciclo_corrigido > 0 else 0.0
    produtividade_m3_h = ciclos_por_hora_teorico * volume_passada * (eficiencia_operador / 100.0)

    if volume_solto_total > 0:
        densidade_solta = tonelagem_total / volume_solto_total
        produtividade_t_h = produtividade_m3_h * densidade_solta
    else:
        produtividade_t_h = 0.0

    horas_totais = (volume_solto_total / produtividade_m3_h) if produtividade_m3_h > 0 else 0.0
    dias_totais = (horas_totais / horas_trabalho_dia) if horas_trabalho_dia > 0 else 0.0

    return {
        'produtividade_m3_h': produtividade_m3_h,
        'produtividade_t_h': produtividade_t_h,
        'horas_totais': horas_totais,
        'dias_totais': dias_totais,
        'tempo_ciclo_corrigido': tempo_ciclo_corrigido
    }

# ==============================================================================
# ROTA HTTP PARA PROCESSAR O FORMULÁRIO DE CARGA
# ==============================================================================
@operacao_bp.route('/operacao', methods=['GET', 'POST'])
def operacao():
    dados_banco = session.get('dados_banco', {})
    volume_solto_raw = dados_banco.get('volume_solto_raw', 0.0)
    tonelagem_raw = dados_banco.get('tonelagem_raw', 0.0)

    if request.method == 'POST':
        modelo_escavadeira = request.form.get('modelo_escavadeira', '').strip()[:100]
        tipo_equipamento = request.form.get('tipo_equipamento', 'backhoe')
        tipo_coroamento = request.form.get('tipo_coroamento', 'heaped_2_1')

        capacidade_concha = parse_float(request.form.get('capacidade_concha'), padrao=15.0, minimo=0.1)
        fator_enchimento = parse_float(request.form.get('fator_enchimento'), padrao=85.0, minimo=1.0)
        tempo_ciclo_segundos = parse_float(request.form.get('tempo_ciclo_segundos'), padrao=32.0, minimo=1.0)
        angulo_giro = parse_int(request.form.get('angulo_giro'), padrao=90, minimo=1)
        eficiencia_operador = parse_float(request.form.get('eficiencia_operador'), padrao=75.0, minimo=1.0)
        horas_trabalho_dia = parse_float(request.form.get('horas_trabalho_dia'), padrao=19.0, minimo=0.1)

        labels_equipamento = {
            'backhoe': 'Escavadeira Hydraulic Backhoe (Inversa)',
            'front_shovel': 'Escavadeira Front Shovel (Pá Frontal)',
            'pa_carregadeira': 'Pá Carregadeira sobre Pneus'
        }
        
        labels_coroamento = {
            'heaped_2_1': 'Coroado Padrão Rocha (SAE 2:1)',
            'heaped_1_1': 'Coroado Material Coesivo (SAE 1:1)',
            'struck': 'Raso / Rente (Struck 1:0)'
        }

        resultado = calcular_operacao_carga(
            volume_solto_total=volume_solto_raw,
            tonelagem_total=tonelagem_raw,
            capacidade_concha=capacidade_concha,
            tipo_coroamento=tipo_coroamento,
            fator_enchimento=fator_enchimento,
            tempo_ciclo_segundos=tempo_ciclo_segundos,
            angulo_giro=angulo_giro,
            eficiencia_operador=eficiencia_operador,
            horas_trabalho_dia=horas_trabalho_dia
        )

        dados_carga = {
            'modelo_escavadeira': modelo_escavadeira,
            'tipo_equipamento': tipo_equipamento,
            'tipo_equipamento_label': labels_equipamento.get(tipo_equipamento, tipo_equipamento),
            'tipo_coroamento': tipo_coroamento,
            'tipo_coroamento_label': labels_coroamento.get(tipo_coroamento, tipo_coroamento),
            'capacidade_concha': capacidade_concha,
            'fator_enchimento': fator_enchimento,
            'tempo_ciclo_segundos': tempo_ciclo_segundos,
            'tempo_ciclo_corrigido': formata_numero(resultado['tempo_ciclo_corrigido']),
            'angulo_giro': angulo_giro,
            'eficiencia_operador': eficiencia_operador,
            'horas_trabalho_dia': horas_trabalho_dia,
            'produtividade_m3_h_formatada': formata_numero(resultado['produtividade_m3_h']),
            'produtividade_t_h_formatada': formata_numero(resultado['produtividade_t_h']),
            'horas_totais_formatada': formata_numero(resultado['horas_totais']),
            'dias_totais_formatado': formata_numero(resultado['dias_totais']),
            'produtividade_m3_h_raw': resultado['produtividade_m3_h'],
            'horas_totais_raw': resultado['horas_totais'],
            'dias_totais_raw': resultado['dias_totais']
        }

        session['dados_carga'] = dados_carga
        return render_template('equipamento_carga.html', dados=dados_carga)

    return render_template('equipamento_carga.html', dados=None)