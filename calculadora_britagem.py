import math
from flask import Blueprint, render_template, request

britagem_bp = Blueprint("britagem", __name__)


def calcular_alimentacao_britagem(
    quantidade_britadores,
    capacidade_nominal_por_britador_tph,
    eficiencia_britagem,
    quantidade_silos,
    quantidade_baias_basculamento,
    tempo_manobra_basculamento_minutos,
    carga_util_toneladas,
    distancia_media_transporte_km,
    velocidade_carregado_kmh,
    velocidade_vazio_kmh,
    tempo_carregamento_fila_minutos,
    eficiencia_frota,
    quantidade_caminhoes,
    horas_turno,
):
    # Validação de segurança para evitar divisão por zero ou valores inválidos
    if (
        quantidade_britadores <= 0
        or capacidade_nominal_por_britador_tph <= 0
        or eficiencia_britagem <= 0
        or quantidade_silos <= 0
        or quantidade_baias_basculamento <= 0
        or tempo_manobra_basculamento_minutos <= 0
        or carga_util_toneladas <= 0
        or distancia_media_transporte_km <= 0
        or velocidade_carregado_kmh <= 0
        or velocidade_vazio_kmh <= 0
        or tempo_carregamento_fila_minutos < 0
        or eficiencia_frota <= 0
        or quantidade_caminhoes <= 0
        or horas_turno <= 0
    ):
        raise ValueError("Todos os parâmetros operacionais devem ser maiores que zero.")

    # 1. Capacidade real de processamento dos britadores
    capacidade_nominal_total_tph = quantidade_britadores * capacidade_nominal_por_britador_tph
    capacidade_real_britagem_tph = capacidade_nominal_total_tph * (eficiencia_britagem / 100)

    # 2. Cálculo real do Tempo de Ciclo pela DMT e Velocidades
    tempo_ida_carregado_minutos = (distancia_media_transporte_km / velocidade_carregado_kmh) * 60
    tempo_volta_vazio_minutos = (distancia_media_transporte_km / velocidade_vazio_kmh) * 60
    tempo_ciclo_total_minutos = (
        tempo_ida_carregado_minutos
        + tempo_volta_vazio_minutos
        + tempo_carregamento_fila_minutos
        + tempo_manobra_basculamento_minutos
    )

    # 3. Capacidade física de recepção dos silos / baias de basculamento
    basculamentos_por_hora_por_baia = 60 / tempo_manobra_basculamento_minutos
    capacidade_recepcao_baias_tph = (
        basculamentos_por_hora_por_baia
        * quantidade_baias_basculamento
        * carga_util_toneladas
    )
    media_baias_por_silo = quantidade_baias_basculamento / quantidade_silos

    # 4. Produtividade efetiva por caminhão (aplicando a eficiência operacional da frota)
    viagens_teoricas_por_hora = 60 / tempo_ciclo_total_minutos
    viagens_efetivas_por_hora = viagens_teoricas_por_hora * (eficiencia_frota / 100)
    producao_por_caminhao_tph = viagens_efetivas_por_hora * carga_util_toneladas
    alimentacao_frota_tph = producao_por_caminhao_tph * quantidade_caminhoes

    chegadas_caminhoes_por_hora = viagens_efetivas_por_hora * quantidade_caminhoes
    intervalo_chegada_minutos = 60 / chegadas_caminhoes_por_hora

    # 5. Taxas de ocupação e dimensionamento recomendado de frota
    taxa_ocupacao_britagem = (alimentacao_frota_tph / capacidade_real_britagem_tph) * 100
    taxa_ocupacao_baias = (alimentacao_frota_tph / capacidade_recepcao_baias_tph) * 100

    diferenca_tph = alimentacao_frota_tph - capacidade_real_britagem_tph
    frota_ideal_exata = capacidade_real_britagem_tph / producao_por_caminhao_tph
    frota_recomendada_inteira = math.ceil(frota_ideal_exata)
    diferenca_caminhoes = frota_recomendada_inteira - quantidade_caminhoes

    if diferenca_caminhoes > 0:
        acao_frota = f"Adicionar +{diferenca_caminhoes} caminhão(ões) para atingir a meta"
    elif diferenca_caminhoes < 0:
        acao_frota = f"Retirar {abs(diferenca_caminhoes)} caminhão(ões) para evitar fila/ociosidade"
    else:
        acao_frota = "Frota atual exata para a capacidade da britagem"

    # 6. Projeção acumulada no turno
    producao_frota_turno_toneladas = alimentacao_frota_tph * horas_turno
    capacidade_britagem_turno_toneladas = capacidade_real_britagem_tph * horas_turno

    # 7. Diagnóstico operacional integrado (Silos/Baias + Britador)
    if taxa_ocupacao_baias > 100:
        status = "Gargalo nos silos/baias (Fila de espera para basculamento)"
    elif taxa_ocupacao_britagem > 105:
        status = "Excesso de frota (Alimentação acima da capacidade do britador)"
    elif taxa_ocupacao_britagem >= 85:
        status = "Operação equilibrada (Britagem e silos em ritmo ideal)"
    else:
        status = "Britador ocioso (Falta transporte para atingir a meta)"

    return {
        "quantidade_silos": quantidade_silos,
        "quantidade_baias_basculamento": quantidade_baias_basculamento,
        "media_baias_por_silo": round(media_baias_por_silo, 1),
        "capacidade_real_britagem_tph": round(capacidade_real_britagem_tph, 1),
        "tempo_ida_carregado_minutos": round(tempo_ida_carregado_minutos, 1),
        "tempo_volta_vazio_minutos": round(tempo_volta_vazio_minutos, 1),
        "tempo_ciclo_total_minutos": round(tempo_ciclo_total_minutos, 1),
        "capacidade_recepcao_baias_tph": round(capacidade_recepcao_baias_tph, 1),
        "taxa_ocupacao_baias": round(taxa_ocupacao_baias, 1),
        "chegadas_caminhoes_por_hora": round(chegadas_caminhoes_por_hora, 1),
        "intervalo_chegada_minutos": round(intervalo_chegada_minutos, 2),
        "viagens_por_hora_caminhao": round(viagens_efetivas_por_hora, 2),
        "producao_por_caminhao_tph": round(producao_por_caminhao_tph, 1),
        "alimentacao_frota_tph": round(alimentacao_frota_tph, 1),
        "taxa_ocupacao_britagem": round(taxa_ocupacao_britagem, 1),
        "diferenca_tph": round(abs(diferenca_tph), 1),
        "tipo_balanco": "Excedente" if diferenca_tph >= 0 else "Déficit",
        "frota_ideal_exata": round(frota_ideal_exata, 1),
        "frota_recomendada_inteira": frota_recomendada_inteira,
        "acao_frota": acao_frota,
        "producao_frota_turno_toneladas": round(producao_frota_turno_toneladas, 1),
        "capacidade_britagem_turno_toneladas": round(capacidade_britagem_turno_toneladas, 1),
        "status": status,
    }


@britagem_bp.route("/britagem", methods=["GET", "POST"])
def pagina_britagem():
    resultado = None
    erro = None
    dados_formulario = {}

    if request.method == "POST":
        dados_formulario = request.form.to_dict()
        try:
            resultado = calcular_alimentacao_britagem(
                quantidade_britadores=int(request.form["quantidade_britadores"]),
                capacidade_nominal_por_britador_tph=float(request.form["capacidade_nominal_por_britador_tph"]),
                eficiencia_britagem=float(request.form["eficiencia_britagem"]),
                quantidade_silos=int(request.form["quantidade_silos"]),
                quantidade_baias_basculamento=int(request.form["quantidade_baias_basculamento"]),
                tempo_manobra_basculamento_minutos=float(request.form["tempo_manobra_basculamento_minutos"]),
                carga_util_toneladas=float(request.form["carga_util_toneladas"]),
                distancia_media_transporte_km=float(request.form["distancia_media_transporte_km"]),
                velocidade_carregado_kmh=float(request.form["velocidade_carregado_kmh"]),
                velocidade_vazio_kmh=float(request.form["velocidade_vazio_kmh"]),
                tempo_carregamento_fila_minutos=float(request.form["tempo_carregamento_fila_minutos"]),
                eficiencia_frota=float(request.form["eficiencia_frota"]),
                quantidade_caminhoes=int(request.form["quantidade_caminhoes"]),
                horas_turno=float(request.form["horas_turno"]),
            )
        except ValueError as falha:
            erro = str(falha)
        except Exception:
            erro = "Preencha todos os campos com valores numéricos válidos."

    return render_template(
        "britagem.html",
        resultado=resultado,
        erro=erro,
        dados_formulario=dados_formulario,
    )