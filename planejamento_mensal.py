from flask import Blueprint, render_template, request
from utils import parse_float, parse_int
from config import MAX_HORAS_MES

planejamento_mensal_app = Blueprint('planejamento_mensal_app', __name__)

MESES_CONFIG = [
    ('Janeiro', 31, 'jan'),
    ('Fevereiro', 28, 'fev'),
    ('Março', 31, 'mar'),
    ('Abril', 30, 'abr'),
    ('Maio', 31, 'mai'),
    ('Junho', 30, 'jun'),
    ('Julho', 31, 'jul'),
    ('Agosto', 31, 'ago'),
    ('Setembro', 30, 'set'),
    ('Outubro', 31, 'out'),
    ('Novembro', 30, 'nov'),
    ('Dezembro', 31, 'dez')
]


def calcular_planejamento_anual(form):
    """Processa todos os parâmetros de turno, paradas, ciclo e chuva/manutenção mensal."""
    nome_contrato = form.get('nome_contrato', 'Contrato Padrão').strip()[:100]
    tipo_material = form.get('tipo_material', 'estoril').strip()[:50]
    material_personalizado = form.get('material_personalizado', '').strip()[:100]

    nome_material_final = (
        material_personalizado if (tipo_material == 'outro' and material_personalizado)
        else tipo_material.capitalize()
    )

    densidade = parse_float(form.get('densidade_material'), padrao=2.70, minimo=0.01)
    meta_producao = parse_float(form.get('volume_anual'), padrao=0.0, minimo=0.0)
    unidade_meta = form.get('unidade_meta', 'toneladas').strip()[:30]
    fator_empolamento = parse_float(form.get('fator_empolamento'), padrao=1.25, minimo=1.0)

    # Regime de turnos e paradas operacionais
    escala_turno = parse_int(form.get('escala_turno'), padrao=12, minimo=1)
    turnos_dia = 2 if escala_turno == 12 else (3 if escala_turno == 8 else 4)

    campos_parada = ['tempo_almoco', 'tempo_jantar', 'tempo_descanso', 'tempo_troca_turno', 'tempo_abastecimento']
    total_paradas_min = sum(parse_float(form.get(campo), padrao=0.0, minimo=0.0) for campo in campos_parada)

    horas_efetivas_turno = max(0.0, escala_turno - (total_paradas_min / 60.0))
    horas_efetivas_dia_total = turnos_dia * horas_efetivas_turno

    # Logística de DMT e tempo de ciclo
    dist_ida = parse_float(form.get('distancia_ida'), padrao=0.0, minimo=0.0)
    dist_volta = parse_float(form.get('distancia_volta'), padrao=0.0, minimo=0.0)
    vel_carregado = parse_float(form.get('vel_carregado'), padrao=20.0, minimo=1.0)
    vel_vazio = parse_float(form.get('vel_vazio'), padrao=35.0, minimo=1.0)
    tempo_fixo_min = parse_float(form.get('tempo_fixo_ciclo'), padrao=0.0, minimo=0.0)

    tempo_ida_horas = (dist_ida / vel_carregado) if vel_carregado > 0 else 0.0
    tempo_volta_horas = (dist_volta / vel_vazio) if vel_vazio > 0 else 0.0
    tempo_ciclo_transporte_min = ((tempo_ida_horas + tempo_volta_horas) * 60.0) + tempo_fixo_min

    # Apuração mensal de horas úteis, chuva e manutenção (limitadas a MAX_HORAS_MES)
    dados_mensais = []
    total_horas_uteis_ano = 0.0
    total_horas_chuva_ano = 0.0
    total_horas_manutencao_ano = 0.0

    for nome_mes, dias_no_mes, sigla in MESES_CONFIG:
        horas_chuva = min(MAX_HORAS_MES, parse_float(form.get(f'chuva_{sigla}'), padrao=0.0, minimo=0.0))
        horas_maint = min(MAX_HORAS_MES, parse_float(form.get(f'maint_{sigla}'), padrao=0.0, minimo=0.0))

        horas_brutas_mes = dias_no_mes * horas_efetivas_dia_total
        horas_uteis_mes = max(0.0, horas_brutas_mes - (horas_chuva + horas_maint))

        total_horas_uteis_ano += horas_uteis_mes
        total_horas_chuva_ano += horas_chuva
        total_horas_manutencao_ano += horas_maint

        dados_mensais.append({
            'mes': nome_mes,
            'horas_uteis': horas_uteis_mes,
            'chuva': horas_chuva,
            'manutencao': horas_maint
        })

    distribuicao_resultado = []
    for item in dados_mensais:
        proporcao = (item['horas_uteis'] / total_horas_uteis_ano) if total_horas_uteis_ano > 0 else (1.0 / 12.0)
        distribuicao_resultado.append({
            'mes': item['mes'],
            'horas_uteis': round(item['horas_uteis'], 1),
            'chuva': item['chuva'],
            'manutencao': item['manutencao'],
            'producao': round(meta_producao * proporcao, 2)
        })

    producao_por_hora = (meta_producao / total_horas_uteis_ano) if total_horas_uteis_ano > 0 else 0.0
    dias_estimados_total = (total_horas_uteis_ano / horas_efetivas_dia_total) if horas_efetivas_dia_total > 0 else 0.0
    meses_estimados = (dias_estimados_total / 30.4375) if dias_estimados_total > 0 else 0.0
    producao_diaria_media = (meta_producao / dias_estimados_total) if dias_estimados_total > 0 else 0.0

    return {
        'contrato': nome_contrato,
        'material': nome_material_final,
        'meta': meta_producao,
        'unidade': unidade_meta,
        'densidade': densidade,
        'empolamento': fator_empolamento,
        'escala': escala_turno,
        'turnos_dia': turnos_dia,
        'horas_efetivas_turno': round(horas_efetivas_turno, 2),
        'horas_efetivas_dia_total': round(horas_efetivas_dia_total, 2),
        'paradas_min': total_paradas_min,
        'dist_ida': dist_ida,
        'dist_volta': dist_volta,
        'vel_carregado': vel_carregado,
        'vel_vazio': vel_vazio,
        'tempo_fixo': tempo_fixo_min,
        'tempo_ciclo': round(tempo_ciclo_transporte_min, 2),
        'distribuicao': distribuicao_resultado,
        'total_horas': round(total_horas_uteis_ano, 1),
        'total_chuva': round(total_horas_chuva_ano, 1),
        'total_manutencao': round(total_horas_manutencao_ano, 1),
        'dias_estimados': round(dias_estimados_total, 1),
        'meses_estimados': round(meses_estimados, 1),
        'prod_hora': round(producao_por_hora, 2),
        'prod_dia': round(producao_diaria_media, 2)
    }


@planejamento_mensal_app.route('/planejamento_mensal', methods=['GET', 'POST'])
def planejamento_mensal():
    if request.method == 'POST':
        try:
            contexto = calcular_planejamento_anual(request.form)
            return render_template('resultado_planejamento.html', **contexto)
        except Exception as e:
            print(f"Erro no cálculo do planejamento: {e}")
            return "Ocorreu um erro ao processar os cálculos operacionais. Verifique os valores informados.", 400

    return render_template('planejamento_mensal.html', max_horas=MAX_HORAS_MES)