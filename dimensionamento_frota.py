"""
Módulo de Rotas e Motor Matemático de Frota e Infraestrutura - MineraCore
Responsável por:
1. Dimensionamento de Carga e Transporte (/dimensionamento_frota)
2. Comparativo Executivo de Cenários (/comparativo_frota)
3. Dimensionamento de Infraestrutura e Apoio (/dimensionamento_infra)
4. Endpoints API em Python para cálculos de frota e infraestrutura (/api/*)

Toda a regra de negócio e matemática permanece concentrada aqui no backend Python,
com sugestões calibradas por classe operacional e sem menção a marcas comerciais.
"""

import math
from flask import Blueprint, jsonify, render_template, request, session
from utils import parse_float

frota_bp = Blueprint('frota_bp', __name__)

# =========================================================================
# 1. CONSTANTES DE CONFIGURAÇÃO, PISO E PRESETS DE EQUIPAMENTOS
# =========================================================================

# Valores padrão caso o usuário acesse diretamente sem passar pelo planejamento anual
PLANO_PADRAO = {
    'contrato': 'Contrato Padrão',
    'material': 'Estéril',
    'densidade': 2.0,
    'empolamento': 1.25,
    'meta_producao': 0.0,
    'unidade_meta': 'toneladas',
    'total_horas_uteis': 0.0,
    'horas_dia': 0.0,
    'prod_dia': 0.0,
    'ritmo_hora': 0.0,
    'dist_ida': 0.0,
    'dist_volta': 0.0,
    'vel_carregado': 20.0,
    'vel_vazio': 30.0,
    'tempo_fixo': 0.0,
    'tempo_ciclo': 0.0
}

# Regras geotécnicas por condição de piso: fator de enchimento (%) e penalidade de ciclo
REGRAS_PISO = {
    'cascalho': {'nome': 'Cascalho / Brita Compactada', 'curto': 'Cascalho', 'enchimento': 92, 'fator_ciclo': 1.00},
    'argila':   {'nome': 'Solo Argiloso / Úmido',       'curto': 'Argila',   'enchimento': 88, 'fator_ciclo': 1.08},
    'rocha':    {'nome': 'Rocha Britada / Fragmentada', 'curto': 'Rocha',    'enchimento': 85, 'fator_ciclo': 1.12},
    'movedico': {'nome': 'Terreno Movediço / Instável', 'curto': 'Movediço', 'enchimento': 84, 'fator_ciclo': 1.15},
}

# Presets de frota primária ordenados do maior ritmo horário (t/h) para o menor (sem marcas comerciais)
PRESETS_FROTA = [
    {
        'min_th': 3000.0,
        'escav': 'Escavadeira Hidráulica Ultra-Pesada (~12,0 m³)',
        'cacamba': 12.0,
        'ciclo': 26.0,
        'cam': 'Caminhão Fora-de-Estrada Rígido (Classe 180–190 t)',
        'carga': 186.0,
        'criterio': 'Ritmo ultra-elevado (>= 3.000 t/h): frota de mineração de grande porte.'
    },
    {
        'min_th': 1500.0,
        'escav': 'Escavadeira Hidráulica de Grande Porte (~6,7 m³)',
        'cacamba': 6.7,
        'ciclo': 24.0,
        'cam': 'Caminhão Fora-de-Estrada Rígido (Classe 100 t)',
        'carga': 96.0,
        'criterio': 'Ritmo elevado (1.500 a 2.999 t/h): alta capacidade de carga e transporte fora de estrada.'
    },
    {
        'min_th': 600.0,
        'escav': 'Escavadeira Hidráulica de Médio/Grande Porte (~5,4 m³)',
        'cacamba': 5.4,
        'ciclo': 22.0,
        'cam': 'Caminhão Articulado / Fora-de-Estrada (Classe 40–45 t)',
        'carga': 41.0,
        'criterio': 'Ritmo médio-alto (600 a 1.499 t/h): escavadeira intermediária e caminhões articulados/fora-de-estrada.'
    },
    {
        'min_th': 0.0,
        'escav': 'Escavadeira Hidráulica de Porte Médio (~2,1 m³)',
        'cacamba': 2.1,
        'ciclo': 20.0,
        'cam': 'Caminhão Basculante Pesado 8x4 (Classe 32 t)',
        'carga': 32.0,
        'criterio': 'Ritmo moderado (< 600 t/h): equilíbrio operacional para frentes de menor porte.'
    },
]

# Normalização de nomes de materiais vindos do planejamento anual
MAPA_MATERIAIS = {
    'itabirito': 'Itabirito Compacto / Minério de Ferro',
    'esteril':   'Estéril / Rocha Sã',
    'estoril':   'Estéril / Rocha Sã',
    'fosfato':   'Minério de Fosfato',
    'argila':    'Argila / Solo de Cobertura',
}


# =========================================================================
# 2. UTILITÁRIOS DE SESSÃO E LEITURA DE DADOS DO PLANO
# =========================================================================

def _normalizar_nome_material(valor):
    """Corrige códigos internos (ex.: 'estoril') para o nome técnico correto."""
    texto = (valor or 'Estéril').strip()[:100]
    return MAPA_MATERIAIS.get(texto.lower(), texto)


def extrair_plano_formulario(form_data):
    """Lê, higieniza e converte os dados enviados pelo formulário de planejamento."""
    return {
        'contrato': form_data.get('contrato', 'Contrato Padrão').strip()[:100],
        'material': _normalizar_nome_material(form_data.get('material')),
        'densidade': parse_float(form_data.get('densidade'), padrao=2.0, minimo=0.01),
        'empolamento': parse_float(form_data.get('empolamento'), padrao=1.25, minimo=1.0),
        'meta_producao': parse_float(form_data.get('meta_producao'), padrao=0.0, minimo=0.0),
        'unidade_meta': form_data.get('unidade_meta', 'toneladas').strip()[:30],
        'total_horas_uteis': parse_float(form_data.get('total_horas_uteis'), padrao=0.0, minimo=0.0),
        'horas_dia': parse_float(form_data.get('horas_dia'), padrao=0.0, minimo=0.0),
        'prod_dia': parse_float(form_data.get('prod_dia'), padrao=0.0, minimo=0.0),
        'ritmo_hora': parse_float(form_data.get('ritmo_hora'), padrao=0.0, minimo=0.0),
        'dist_ida': parse_float(form_data.get('dist_ida'), padrao=0.0, minimo=0.0),
        'dist_volta': parse_float(form_data.get('dist_volta'), padrao=0.0, minimo=0.0),
        'vel_carregado': parse_float(form_data.get('vel_carregado'), padrao=20.0, minimo=1.0),
        'vel_vazio': parse_float(form_data.get('vel_vazio'), padrao=30.0, minimo=1.0),
        'tempo_fixo': parse_float(form_data.get('tempo_fixo'), padrao=0.0, minimo=0.0),
        'tempo_ciclo': parse_float(form_data.get('tempo_ciclo'), padrao=0.0, minimo=0.0),
    }


def obter_plano_sessao():
    """Recupera o plano ativo da sessão do usuário ou retorna o plano padrão."""
    plano = dict(session.get('plano_frota', PLANO_PADRAO))
    plano['material'] = _normalizar_nome_material(plano.get('material'))
    return plano


def _obter_regra_piso(chave_piso):
    """Retorna a configuração geotécnica do piso ou 'cascalho' como fallback."""
    return REGRAS_PISO.get((chave_piso or '').strip().lower(), REGRAS_PISO['cascalho'])


def _classificar_piso_texto(nome_piso):
    """
    Identifica a chave interna do piso ('rocha', 'argila', 'movedico' ou 'cascalho')
    a partir da descrição textual salva no cenário primário.
    """
    piso = (nome_piso or '').lower()
    if 'rocha' in piso:
        return 'rocha'
    if 'argil' in piso:
        return 'argila'
    if 'movedi' in piso:
        return 'movedico'
    return 'cascalho'


# =========================================================================
# 3. MOTOR MATEMÁTICO — FROTA DE PRODUÇÃO (CARGA E TRANSPORTE)
# =========================================================================

def _calcular_preview_escavadeira(inputs, plano):
    """Calcula massa por passe, produção unitária (t/h) e classificação de porte."""
    cacamba = parse_float(inputs.get('cacamba'), padrao=0.0, minimo=0.0)
    ciclo_seg = parse_float(inputs.get('cicloEscav'), padrao=0.0, minimo=0.0)
    enchimento_pct = parse_float(inputs.get('fatorEnchimentoPct'), padrao=90.0, minimo=1.0)
    efic_escav_pct = parse_float(inputs.get('eficEscavPct'), padrao=83.0, minimo=1.0)

    densidade = parse_float(plano.get('densidade'), padrao=2.0, minimo=0.01)
    empolamento = parse_float(plano.get('empolamento'), padrao=1.25, minimo=1.0)
    densidade_solta = densidade / empolamento

    if cacamba <= 0:
        return {
            'classe_porte': 'Classe Carga',
            'massa_passe_texto': '-- t',
            'prod_unit_texto': '-- t/h'
        }

    massa_passe = cacamba * (enchimento_pct / 100.0) * densidade_solta
    prod_unit = (3600.0 / ciclo_seg) * (efic_escav_pct / 100.0) * massa_passe if ciclo_seg > 0 else 0.0

    if cacamba >= 12.0:
        classe_porte = 'Mineração Ultra-Pesada (200t+)'
    elif cacamba >= 6.0:
        classe_porte = 'Mineração Média/Pesada (90t–140t)'
    else:
        classe_porte = 'Apoio / Pequeno Porte (35t–50t)'

    return {
        'classe_porte': classe_porte,
        'massa_passe_texto': f"{massa_passe:.2f} t",
        'prod_unit_texto': f"{prod_unit:.1f} t/h" if prod_unit > 0 else '-- t/h'
    }


def _sugerir_frota_producao(acao, inputs, plano):
    """Atende sugestões de piso, preview da escavadeira ou preset completo de frota."""
    regra_piso = _obter_regra_piso(inputs.get('perfilPiso'))

    if acao == 'piso':
        return {'fator_enchimento_pct': regra_piso['enchimento']}

    if acao == 'preview':
        return _calcular_preview_escavadeira(inputs, plano)

    ritmo_alvo_th = parse_float(plano.get('ritmo_hora'), padrao=0.0, minimo=0.0)
    preset = next((p for p in PRESETS_FROTA if ritmo_alvo_th >= p['min_th']), PRESETS_FROTA[-1])

    return {
        'fator_enchimento_pct': regra_piso['enchimento'],
        'modEscav': preset['escav'],
        'cacamba': preset['cacamba'],
        'cicloEscav': preset['ciclo'],
        'eficEscavPct': 83,
        'modCam': preset['cam'],
        'cargaCaminhao': preset['carga'],
        'eficTranspPct': 85,
        'margemFalhaPct': 10,
        'criterio': preset['criterio']
    }


def _classificar_match_factor(mf):
    """Retorna status textual e classe CSS para o indicador Match Factor."""
    if mf < 0.95:
        return 'Subdimensionado (< 0.95)', 'mf-alerta'
    if mf > 1.05:
        return 'Saturado (> 1.05)', 'mf-saturado'
    return 'Equilibrado (0.95 a 1.05)', 'mf-ok'


def _simular_frota_producao(inputs, plano, criterio=''):
    """Executa o dimensionamento de carga, transporte, rodagem e match factor."""
    cacamba = parse_float(inputs.get('cacamba'), padrao=0.0, minimo=0.0)
    ciclo_escav_seg = parse_float(inputs.get('cicloEscav'), padrao=0.0, minimo=0.0)
    carga_cam_t = parse_float(inputs.get('cargaCaminhao'), padrao=0.0, minimo=0.0)

    if cacamba <= 0 or ciclo_escav_seg <= 0 or carga_cam_t <= 0:
        return {'erro': 'Preencha a caçamba da escavadeira, o tempo de ciclo e a carga útil do caminhão.'}

    # Parâmetros operacionais e geotécnicos
    regra_piso = _obter_regra_piso(inputs.get('perfilPiso'))
    margem_falha_pct = parse_float(inputs.get('margemFalhaPct'), padrao=10.0, minimo=0.0)
    enchimento_pct = parse_float(inputs.get('fatorEnchimentoPct'), padrao=regra_piso['enchimento'], minimo=1.0)
    efic_escav_pct = parse_float(inputs.get('eficEscavPct'), padrao=83.0, minimo=1.0)
    efic_transp_pct = parse_float(inputs.get('eficTranspPct'), padrao=85.0, minimo=1.0)

    mod_escav = (inputs.get('modEscav') or 'Escavadeira').strip()
    mod_cam = (inputs.get('modCam') or 'Caminhão').strip()

    # Densidade solta e metas do contrato
    densidade = parse_float(plano.get('densidade'), padrao=2.0, minimo=0.01)
    empolamento = parse_float(plano.get('empolamento'), padrao=1.25, minimo=1.0)
    densidade_solta = densidade / empolamento

    ritmo_alvo_th = parse_float(plano.get('ritmo_hora'), padrao=0.0, minimo=0.0)
    ritmo_com_reserva_th = ritmo_alvo_th * (1.0 + (margem_falha_pct / 100.0))

    # Perfil viário e tempos de ciclo base
    dist_ida = parse_float(plano.get('dist_ida'), padrao=0.0, minimo=0.0)
    dist_volta = parse_float(plano.get('dist_volta'), padrao=dist_ida, minimo=0.0)
    dmt_ida_volta = dist_ida + dist_volta

    vel_carregado = parse_float(plano.get('vel_carregado'), padrao=20.0, minimo=1.0)
    vel_vazio = parse_float(plano.get('vel_vazio'), padrao=30.0, minimo=1.0)
    tempo_fixo_min = parse_float(plano.get('tempo_fixo'), padrao=0.0, minimo=0.0)
    horas_uteis_ano = parse_float(plano.get('total_horas_uteis'), padrao=0.0, minimo=0.0)

    # 1. Acoplamento caçamba x caminhão (massa por passe e passes necessários)
    toneladas_passe = cacamba * (enchimento_pct / 100.0) * densidade_solta
    passadas = max(1, round(carga_cam_t / max(0.01, toneladas_passe)))
    carga_real = passadas * toneladas_passe
    fator_carregamento_pct = (carga_real / max(0.01, carga_cam_t)) * 100.0

    # 2. Produtividade unitária da escavadeira (t/h)
    tempo_carga_min = (passadas * ciclo_escav_seg) / 60.0
    efic_escav = efic_escav_pct / 100.0
    prod_escav_th = (3600.0 / ciclo_escav_seg) * efic_escav * toneladas_passe

    # 3. Ciclo total e produtividade unitária do caminhão (t/h)
    tempo_ida_min = (dist_ida / vel_carregado) * 60.0 if vel_carregado > 0 else 0.0
    tempo_volta_min = (dist_volta / vel_vazio) * 60.0 if vel_vazio > 0 else 0.0
    ciclo_total_min = max(1.0, (tempo_ida_min + tempo_volta_min + tempo_fixo_min + tempo_carga_min) * regra_piso['fator_ciclo'])

    efic_transp = efic_transp_pct / 100.0
    viagens_hora_cam = (60.0 / ciclo_total_min) * efic_transp
    prod_cam_th = viagens_hora_cam * carga_real

    # 4. Dimensionamento da frota com reserva técnica
    qtd_escav = max(1, math.ceil(ritmo_com_reserva_th / max(0.1, prod_escav_th))) if ritmo_com_reserva_th > 0 else 1
    qtd_cam = max(1, math.ceil(ritmo_com_reserva_th / max(0.1, prod_cam_th))) if ritmo_com_reserva_th > 0 else 1

    # 5. Match Factor: (Qtd Caminhões * Tempo Carga) / (Qtd Escavadeiras * Ciclo Caminhão)
    match_factor = (qtd_cam * tempo_carga_min) / max(0.01, (qtd_escav * ciclo_total_min))
    status_mf, classe_mf = _classificar_match_factor(match_factor)

    cap_carga_th = qtd_escav * prod_escav_th
    cap_transp_th = qtd_cam * prod_cam_th
    relacao_cam_escav = qtd_cam / max(1, qtd_escav)

    # 6. Rodagem operacional da frota de transporte
    km_total_hora = qtd_cam * viagens_hora_cam * dmt_ida_volta
    km_total_ano = km_total_hora * horas_uteis_ano

    # 7. Alertas e diagnóstico de engenharia
    alertas = [
        f"⚙️ <strong>Acoplamento:</strong> {status_mf} (MF {match_factor:.2f}) com {passadas} passe(s) por caminhão.",
        f"🚛 <strong>Capacidade Instalada:</strong> {cap_carga_th:.0f} t/h em carga e {cap_transp_th:.0f} t/h em transporte (meta: {ritmo_com_reserva_th:.0f} t/h com reserva)."
    ]
    if passadas < 3 or passadas > 6:
        alertas.append(f"⚠️ <strong>Número de Passes ({passadas}):</strong> O ideal operacional costuma ficar entre 3 e 6 passes para evitar sub ou sobrecarregamento.")

    inputs_normalizados = {
        'perfilPiso': inputs.get('perfilPiso') or 'cascalho',
        'margemFalhaPct': margem_falha_pct,
        'modEscav': mod_escav,
        'cacamba': cacamba,
        'fatorEnchimentoPct': enchimento_pct,
        'cicloEscav': ciclo_escav_seg,
        'eficEscavPct': efic_escav_pct,
        'modCam': mod_cam,
        'cargaCaminhao': carga_cam_t,
        'eficTranspPct': efic_transp_pct,
    }

    simulacao = {
        'criterio': criterio,
        'nomePiso': regra_piso['nome'],
        'pisoCurto': regra_piso['curto'],
        'margemFalhaPct': round(margem_falha_pct, 1),
        'toneladasPasse': round(toneladas_passe, 2),
        'passadas': passadas,
        'cargaReal': round(carga_real, 1),
        'fatorCarregamentoPct': round(fator_carregamento_pct, 0),
        'tempoCargaMin': round(tempo_carga_min, 2),
        'cicloTotalMin': round(ciclo_total_min, 2),
        'qtdEscavadeiras': qtd_escav,
        'qtdCaminhoes': qtd_cam,
        'totalMaquinas': qtd_escav + qtd_cam,
        'escavNominal': mod_escav,
        'camNominal': mod_cam,
        'prodEscavadeiraTH': round(prod_escav_th, 1),
        'prodPorCaminhaoTH': round(prod_cam_th, 1),
        'capCargaTH': round(cap_carga_th, 0),
        'capTranspTH': round(cap_transp_th, 0),
        'matchFactor': round(match_factor, 2),
        'statusMF': status_mf,
        'classeMF': classe_mf,
        'relacaoFrotaTexto': f"~{relacao_cam_escav:.1f} caminhões / escavadeira",
        'dmtIdaKm': dist_ida,
        'dmtVoltaKm': dist_volta,
        'kmTotalHora': round(km_total_hora, 1),
        'kmTotalAno': round(km_total_ano, 0),
        'alertas': alertas,
        'inputs': inputs_normalizados
    }

    return {'simulacao': simulacao}


# =========================================================================
# 4. MOTOR MATEMÁTICO — COMPARATIVO EXECUTIVO DE CENÁRIOS
# =========================================================================

def _gerar_parecer_comparativo(cenarios):
    """Avalia equilíbrio operacional (MF), passes e porte de frota para indicar o melhor cenário."""
    if len(cenarios) == 1:
        c = cenarios[0]
        nome = c.get('nome') or 'Opção 1'
        return nome, (
            f"Apenas a opção '{nome}' está gravada no momento "
            f"({c.get('qtdEscavadeiras', 0)} escavadeira(s) + {c.get('qtdCaminhoes', 0)} caminhão(ões), "
            f"MF {parse_float(c.get('matchFactor'), 0.0):.2f} e {int(parse_float(c.get('passadas'), 0))} passes/ciclo). "
            f"Grave uma segunda opção na tela anterior para confrontar alternativas."
        )

    def pontuacao_cenario(c):
        mf = parse_float(c.get('matchFactor'), 1.0)
        passes = int(parse_float(c.get('passadas'), 4))
        total_maq = int(parse_float(c.get('qtdEscavadeiras'), 0)) + int(parse_float(c.get('qtdCaminhoes'), 0))
        penalidade_passes = 0.0 if 3 <= passes <= 6 else 0.35
        return abs(1.0 - mf) + penalidade_passes + (total_maq * 0.01)

    vencedor = min(cenarios, key=pontuacao_cenario)
    nome_vencedor = vencedor.get('nome') or 'Opção Recomendada'
    mf_v = parse_float(vencedor.get('matchFactor'), 0.0)
    maq_v = int(parse_float(vencedor.get('qtdEscavadeiras'), 0)) + int(parse_float(vencedor.get('qtdCaminhoes'), 0))

    parecer = (
        f"'{nome_vencedor}' apresenta o melhor compromisso técnico-operacional: "
        f"frota total de {maq_v} equipamentos, Match Factor de {mf_v:.2f} "
        f"e {int(parse_float(vencedor.get('passadas'), 0))} passes por ciclo."
    )
    return nome_vencedor, parecer


def _comparar_cenarios_producao(cenarios, plano):
    """Compara os cenários salvos (até 2), gera o parecer técnico e retorna os cartões."""
    if not cenarios:
        return {'cards': [], 'recomendado': '', 'parecer': ''}

    horas_uteis_ano = parse_float(plano.get('total_horas_uteis'), padrao=0.0, minimo=0.0)

    elegiveis_mf = [c for c in cenarios if 3 <= int(parse_float(c.get('passadas'), 0)) <= 6]
    melhor_mf_id = None
    if len(cenarios) > 1 and elegiveis_mf:
        melhor_mf_id = min(elegiveis_mf, key=lambda c: abs(1.0 - parse_float(c.get('matchFactor'), 1.0))).get('id')

    base = cenarios[0]
    maq_base = int(parse_float(base.get('qtdEscavadeiras'), 0)) + int(parse_float(base.get('qtdCaminhoes'), 0))

    cards = []
    for idx, c in enumerate(cenarios):
        qtd_e = int(parse_float(c.get('qtdEscavadeiras'), 0))
        qtd_c = int(parse_float(c.get('qtdCaminhoes'), 0))
        total_maq = qtd_e + qtd_c

        km_hora = parse_float(c.get('kmTotalHora'), 0.0)
        km_ano = parse_float(c.get('kmTotalAno'), km_hora * horas_uteis_ano)

        is_melhor = (c.get('id') == melhor_mf_id)

        if idx == 0:
            badge_opcao = 'OPÇÃO 1 (BASE)'
        else:
            diff_maq = total_maq - maq_base
            sinal_maq = '+' if diff_maq > 0 else ''
            badge_opcao = f"OPÇÃO 2 ({sinal_maq}{diff_maq} máq.)"

        badge_destaque = '<span class="badge-recomendado">⭐ MELHOR EQUILÍBRIO</span>' if is_melhor else ''

        inputs_c = c.get('inputs') or {}
        cards.append({
            'id': c.get('id'),
            'nome': c.get('nome') or f"Opção {idx + 1}",
            'nomePiso': c.get('nomePiso') or '--',
            'badgeOpcao': badge_opcao,
            'badgeDestaque': badge_destaque,
            'corBorda': '#10b981' if is_melhor else '#26334d',
            'totalMaquinas': total_maq,
            'qtdEscavadeiras': qtd_e,
            'qtdCaminhoes': qtd_c,
            'matchFactor': f"{parse_float(c.get('matchFactor'), 0.0):.2f}",
            'passadas': int(parse_float(c.get('passadas'), 0)),
            'modEscav': inputs_c.get('modEscav') or c.get('escavNominal') or 'Escavadeira',
            'cacamba': inputs_c.get('cacamba') or 0,
            'capCargaTH': f"{parse_float(c.get('capCargaTH'), 0.0):.0f}",
            'modCam': inputs_c.get('modCam') or c.get('camNominal') or 'Caminhão',
            'cargaCaminhao': inputs_c.get('cargaCaminhao') or 0,
            'capTranspTH': f"{parse_float(c.get('capTranspTH'), 0.0):.0f}",
            'kmTotalHora': f"{km_hora:.1f}",
            'kmTotalAno': round(km_ano)
        })

    recomendado, parecer = _gerar_parecer_comparativo(cenarios)
    return {'cards': cards, 'recomendado': recomendado, 'parecer': parecer}


# =========================================================================
# 5. MOTOR MATEMÁTICO DE INFRAESTRUTURA E APOIO (MÓDULO INFRA)
# =========================================================================

def _sugerir_infraestrutura_apoio(cenario, plano):
    """
    [INFRAESTRUTURA — SUGESTÃO AUTOMÁTICA DE EQUIPAMENTOS]
    Analisa a tonelagem real dos caminhões, quantidade de escavadeiras e tipo de piso
    do cenário selecionado para recomendar portes compatíveis (sem marcas comerciais).
    """
    cenario = cenario or {}
    inputs_cenario = cenario.get('inputs') or {}

    qtd_cam = int(parse_float(cenario.get('qtdCaminhoes'), padrao=0, minimo=0))
    qtd_escav = int(parse_float(cenario.get('qtdEscavadeiras'), padrao=0, minimo=0))
    carga_cam = parse_float(inputs_cenario.get('cargaCaminhao'), padrao=0.0, minimo=0.0)
    piso_chave = _classificar_piso_texto(cenario.get('nomePiso'))

    # 1. Sugestão de porte da Motoniveladora (Patrol) conforme tonelagem dos caminhões
    if carga_cam >= 130:
        mod_patrol = 'Porte Ultra-Pesado — Lâmina 24 pés (> 500 HP | Caminhões > 130 t)'
    elif carga_cam >= 60 or qtd_cam >= 18:
        mod_patrol = 'Porte Pesado — Lâmina 16 pés (~300–350 HP | Caminhões 60–120 t)'
    elif carga_cam >= 40 or qtd_cam >= 8:
        mod_patrol = 'Porte Médio/Pesado — Lâmina 14 a 16 pés (~250–300 HP)'
    else:
        mod_patrol = 'Porte Médio — Lâmina 14 pés (~190–250 HP | Caminhões até 40 t)'

    # 2. Sugestão de porte do Trator de Esteiras conforme porte da frota de carga/transporte
    if carga_cam >= 130 or qtd_escav >= 4:
        mod_trator = 'Trator de Esteiras Ultra-Pesado (> 550 HP | Alta Produção)'
    elif carga_cam >= 60 or qtd_escav >= 3:
        mod_trator = 'Trator de Esteiras Pesado (400–500 HP | Praça e Bota-Fora)'
    elif carga_cam >= 40 or qtd_escav >= 2:
        mod_trator = 'Trator de Esteiras Médio/Pesado (300–350 HP)'
    else:
        mod_trator = 'Trator de Esteiras Médio (~200–250 HP | Praça & Apoio)'

    # 3. Sugestão de capacidade do Caminhão-Pipa
    if carga_cam >= 130:
        mod_pipa = 'Caminhão-Pipa Fora-de-Estrada (50.000 L a 75.000 L)'
        volume_pipa = 60000
    elif carga_cam >= 50:
        mod_pipa = 'Caminhão-Pipa Fora-de-Estrada (30.000 L)'
        volume_pipa = 30000
    else:
        mod_pipa = 'Caminhão-Pipa Pesado (20.000 L)'
        volume_pipa = 20000

    ciclo_pipa = 40 if piso_chave == 'rocha' else 45
    frentes_sugeridas = max(1, min(6, math.ceil(max(1, qtd_escav) / 2)))
    dist_ida = parse_float(plano.get('dist_ida'), padrao=3.0, minimo=0.1)

    return {
        'patrol': {'modelo': mod_patrol, 'extensao_km': round(dist_ida, 1), 'efic': 80},
        'trator': {'modelo': mod_trator, 'frentes': frentes_sugeridas, 'efic': 80},
        'pipa':   {'modelo': mod_pipa,   'volume': volume_pipa,          'ciclo': ciclo_pipa}
    }


def _calcular_infraestrutura_apoio(dados, cenario, plano):
    """
    [INFRAESTRUTURA — CÁLCULO COMPLETO DA FROTA DE APOIO E CONSOLIDAÇÃO DA MINA]
    Executa toda a matemática de dimensionamento de Patrol, Trator, Pipa e Extras,
    soma ao efetivo primário (escavadeiras + caminhões) e gera os alertas técnicos.
    """
    cenario = cenario or {}
    inputs_cenario = cenario.get('inputs') or {}
    dist_padrao = parse_float(plano.get('dist_ida'), padrao=1.0, minimo=0.1)

    # Efetivo e porte da frota primária herdada do comparativo
    qtd_escav = int(parse_float(cenario.get('qtdEscavadeiras'), padrao=0, minimo=0))
    qtd_cam = int(parse_float(cenario.get('qtdCaminhoes'), padrao=0, minimo=0))
    carga_cam = parse_float(inputs_cenario.get('cargaCaminhao'), padrao=0.0, minimo=0.0)
    qtd_primaria = qtd_escav + qtd_cam

    # Fatores geotécnicos e climáticos aplicados à infraestrutura
    piso_chave = _classificar_piso_texto(cenario.get('nomePiso'))
    fator_piso_patrol = 1.25 if piso_chave == 'rocha' else (1.20 if piso_chave == 'movedico' else 1.0)
    fator_clima_pipa = 0.75 if piso_chave in ('argila', 'movedico') else 1.0

    # --- 1. DIMENSIONAMENTO DA MOTONIVELADORA (PATROL) ---
    modelo_patrol = (dados.get('modelo_patrol') or '').strip() or 'Motoniveladora (Personalizada)'
    extensao_km = parse_float(dados.get('extensao_pista_km'), padrao=dist_padrao, minimo=0.1)
    efic_patrol = max(0.30, parse_float(dados.get('efic_patrol'), padrao=80.0, minimo=30.0) / 100.0)
    fator_fluxo = 1.0 + min(0.60, max(1, qtd_cam) / 60.0)
    qtd_patrol = max(1, math.ceil((((extensao_km * 2.0 * fator_piso_patrol) / 6.0) * fator_fluxo) / efic_patrol))

    # --- 2. DIMENSIONAMENTO DO TRATOR DE ESTEIRAS (PRAÇA & BOTA-FORA) ---
    modelo_trator = (dados.get('modelo_trator') or '').strip() or 'Trator de Esteiras (Personalizado)'
    frentes = int(parse_float(dados.get('frentes_bota_fora'), padrao=1, minimo=1))
    efic_trator = max(0.30, parse_float(dados.get('efic_trator'), padrao=80.0, minimo=30.0) / 100.0)
    qtd_trator = max(1, math.ceil(((frentes * 0.65) + (qtd_escav * 0.25)) / efic_trator))

    # --- 3. DIMENSIONAMENTO DO CAMINHÃO-PIPA (UMECTAÇÃO DE VIAS) ---
    modelo_pipa = (dados.get('modelo_pipa') or '').strip() or 'Caminhão-Pipa (Personalizado)'
    volume_l = parse_float(dados.get('capacidade_pipa_l'), padrao=30000.0, minimo=1000.0)
    ciclo_min = parse_float(dados.get('ciclo_reabastecimento_min'), padrao=45.0, minimo=5.0)
    efic_pipa = 0.80
    demanda_agua_hora_l = extensao_km * (3800.0 * fator_clima_pipa) * 2.5
    cap_hora_pipa_l = volume_l * (60.0 / ciclo_min) * efic_pipa
    qtd_pipa = max(1, math.ceil(demanda_agua_hora_l / max(1.0, cap_hora_pipa_l)))

    # --- 4. PROCESSAMENTO DOS EQUIPAMENTOS EXTRAS DO USUÁRIO (ATÉ 3) ---
    extras_recebidos = (dados.get('extras') or [])[:3]
    extras_validas = []
    for idx, item in enumerate(extras_recebidos):
        if not isinstance(item, dict):
            continue
        nome_extra = (item.get('nome') or '').strip() or f'Máquina Extra {idx + 1}'
        qtd_extra = int(parse_float(item.get('qtd'), padrao=0, minimo=0))
        if qtd_extra > 0:
            extras_validas.append({
                'nome': nome_extra,
                'qtd': qtd_extra
            })

    extra_qtd_total = sum(item['qtd'] for item in extras_validas)

    # --- 5. CONSOLIDAÇÃO GERAL DA FROTA DA MINA (PRIMÁRIA + APOIO) ---
    total_equipamentos_infra = qtd_patrol + qtd_trator + qtd_pipa + extra_qtd_total
    total_equipamentos_mina = qtd_primaria + total_equipamentos_infra

    # --- 6. DIAGNÓSTICO E ALERTAS TÉCNICOS DE INFRAESTRUTURA ---
    alertas = [
        (
            f"⚠️ <strong>Extensão Viária ({extensao_km:.1f} km):</strong> Apenas 1 motoniveladora pode comprometer o perfil da pista em trechos longos."
            if (extensao_km > 6.0 and qtd_patrol == 1)
            else f"✅ <strong>Manutenção de Vias:</strong> {qtd_patrol} motoniveladora(s) dimensionada(s) para {extensao_km:.1f} km de vias."
        ),
        (
            f"⚠️ <strong>Relação Trator x Caminhões:</strong> {qtd_cam} caminhões para {qtd_trator} trator(es) de esteiras pode gerar filas na descarga/praça."
            if (qtd_cam > 0 and (qtd_cam / qtd_trator) > 18.0)
            else f"✅ <strong>Praça & Bota-Fora:</strong> {qtd_trator} trator(es) de esteiras para {frentes} frente(s) ativa(s)."
        ),
        f"💧 <strong>Supressão de Poeira:</strong> Demanda estimada de {round(demanda_agua_hora_l):,} L/h atendida por {qtd_pipa} caminhão(ões)-pipa ({int(volume_l):,} L).".replace(',', '.')
    ]

    # Alerta de compatibilidade de porte da Patrol vs. Tonelagem do Caminhão
    patrol_lower = modelo_patrol.lower()
    if carga_cam >= 130 and any(cod in patrol_lower for cod in ('14', '16', '140', '160')):
        alertas.insert(0, (
            f"🚨 <strong>Subdimensionamento de Patrol:</strong> Caminhões de {carga_cam:.0f} t exigem largura de pista e esforço de corte compatíveis com "
            f"motoniveladora <strong>Porte Ultra-Pesado (Lâmina 24 pés)</strong>."
        ))

    for item in extras_validas:
        alertas.append(f"🛠️ <strong>{item['nome']}:</strong> {item['qtd']} unidade(s) adicionada(s) à frota de apoio.")

    return {
        'qtd_patrol': qtd_patrol,
        'modelo_patrol': modelo_patrol,
        'extensao_km': extensao_km,
        'qtd_trator': qtd_trator,
        'modelo_trator': modelo_trator,
        'frentes_bota_fora': frentes,
        'qtd_pipa': qtd_pipa,
        'modelo_pipa': modelo_pipa,
        'demanda_agua_hora_l': round(demanda_agua_hora_l),
        'extras_validas': extras_validas,
        'qtd_primaria': qtd_primaria,
        'total_equipamentos_infra': total_equipamentos_infra,
        'total_equipamentos_mina': total_equipamentos_mina,
        'alertas': alertas
    }


# =========================================================================
# 6. ROTAS DE PÁGINAS (HTML)
# =========================================================================

@frota_bp.route('/dimensionamento_frota', methods=['GET', 'POST'])
def dimensionamento_frota():
    """Renderiza a tela de dimensionamento de carga e transporte."""
    if request.method == 'POST':
        try:
            plano = extrair_plano_formulario(request.form)
            session['plano_frota'] = plano
            return render_template('dimensionamento_frota.html', plano=plano)
        except Exception as erro:
            print(f"Erro ao transitar para o dimensionamento de frota: {erro}")
            return "Erro ao carregar dados para a próxima etapa.", 400

    return render_template('dimensionamento_frota.html', plano=obter_plano_sessao())


@frota_bp.route('/comparativo_frota', methods=['GET'])
def comparativo_frota():
    """Renderiza o estudo comparativo lado a lado (Opção 1 vs. Opção 2)."""
    return render_template('comparativo_frota.html', plano=obter_plano_sessao())


@frota_bp.route('/dimensionamento_infra', methods=['GET'])
def dimensionamento_infra():
    """[INFRAESTRUTURA — ROTA HTML] Renderiza a página de infraestrutura e equipamentos de apoio."""
    return render_template('dimensionamento_infra.html', plano=obter_plano_sessao())


# =========================================================================
# 7. ROTAS API (JSON) — PROCESSAMENTO EXCLUSIVO NO BACKEND PYTHON
# =========================================================================

@frota_bp.route('/api/sugerir_frota', methods=['POST'])
def api_sugerir_frota():
    """Retorna ajuste de piso, preview da escavadeira ou sugestão de frota compatível."""
    payload = request.get_json(silent=True) or {}
    acao = payload.get('acao', 'preset')
    inputs = payload.get('inputs') or {}
    return jsonify(_sugerir_frota_producao(acao, inputs, obter_plano_sessao()))


@frota_bp.route('/api/simular_frota', methods=['POST'])
def api_simular_frota():
    """Calcula a frota ideal de escavadeiras e caminhões para os parâmetros enviados."""
    payload = request.get_json(silent=True) or {}
    inputs = payload.get('inputs') or {}
    criterio = payload.get('criterio') or ''
    return jsonify(_simular_frota_producao(inputs, obter_plano_sessao(), criterio))


@frota_bp.route('/api/comparar_cenarios', methods=['POST'])
def api_comparar_cenarios():
    """Compara os cenários salvos e devolve os cards e o parecer técnico."""
    payload = request.get_json(silent=True) or {}
    cenarios = payload.get('cenarios') or []
    return jsonify(_comparar_cenarios_producao(cenarios, obter_plano_sessao()))


# --- ENDPOINTS API EXCLUSIVOS DO MÓDULO DE INFRAESTRUTURA E APOIO ---

@frota_bp.route('/api/sugerir_infra', methods=['POST'])
def api_sugerir_infra():
    """[INFRAESTRUTURA — API] Sugere patrol, trator de esteiras e pipa compatíveis com o cenário escolhido."""
    payload = request.get_json(silent=True) or {}
    cenario = payload.get('cenario') or {}
    return jsonify(_sugerir_infraestrutura_apoio(cenario, obter_plano_sessao()))


@frota_bp.route('/api/calcular_infra', methods=['POST'])
def api_calcular_infra():
    """[INFRAESTRUTURA — API] Calcula a frota de infraestrutura (incluindo extras) e o efetivo global da mina."""
    payload = request.get_json(silent=True) or {}
    dados = payload.get('inputs') or {}
    cenario = payload.get('cenario') or {}
    return jsonify(_calcular_infraestrutura_apoio(dados, cenario, obter_plano_sessao()))