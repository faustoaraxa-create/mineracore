from flask import Blueprint, render_template, request, session
from utils import parse_float

frota_bp = Blueprint('frota_bp', __name__)

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


@frota_bp.route('/dimensionamento_frota', methods=['GET', 'POST'])
def dimensionamento_frota():
    if request.method == 'POST':
        try:
            plano = {
                'contrato': request.form.get('contrato', 'Contrato Padrão').strip()[:100],
                'material': request.form.get('material', 'Estéril').strip()[:100],
                'densidade': parse_float(request.form.get('densidade'), padrao=2.0, minimo=0.01),
                'empolamento': parse_float(request.form.get('empolamento'), padrao=1.25, minimo=1.0),
                'meta_producao': parse_float(request.form.get('meta_producao'), padrao=0.0, minimo=0.0),
                'unidade_meta': request.form.get('unidade_meta', 'toneladas').strip()[:30],
                'total_horas_uteis': parse_float(request.form.get('total_horas_uteis'), padrao=0.0, minimo=0.0),
                'horas_dia': parse_float(request.form.get('horas_dia'), padrao=0.0, minimo=0.0),
                'prod_dia': parse_float(request.form.get('prod_dia'), padrao=0.0, minimo=0.0),
                'ritmo_hora': parse_float(request.form.get('ritmo_hora'), padrao=0.0, minimo=0.0),
                'dist_ida': parse_float(request.form.get('dist_ida'), padrao=0.0, minimo=0.0),
                'dist_volta': parse_float(request.form.get('dist_volta'), padrao=0.0, minimo=0.0),
                'vel_carregado': parse_float(request.form.get('vel_carregado'), padrao=20.0, minimo=1.0),
                'vel_vazio': parse_float(request.form.get('vel_vazio'), padrao=30.0, minimo=1.0),
                'tempo_fixo': parse_float(request.form.get('tempo_fixo'), padrao=0.0, minimo=0.0),
                'tempo_ciclo': parse_float(request.form.get('tempo_ciclo'), padrao=0.0, minimo=0.0),
            }

            session['plano_frota'] = plano
            return render_template('dimensionamento_frota.html', plano=plano)

        except Exception as e:
            print(f"Erro ao transitar para o dimensionamento de frota: {e}")
            return "Erro ao carregar dados para a próxima etapa.", 400

    # Permite recarregar a página via GET usando os dados já salvos na sessão
    plano = session.get('plano_frota', PLANO_PADRAO)
    return render_template('dimensionamento_frota.html', plano=plano)


@frota_bp.route('/comparativo_frota', methods=['GET'])
def comparativo_frota():
    plano = session.get('plano_frota', PLANO_PADRAO)
    return render_template('comparativo_frota.html', plano=plano)