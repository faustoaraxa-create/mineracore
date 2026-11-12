from flask import Blueprint, render_template, request, session
from utils import parse_float, formata_numero

lavra_bp = Blueprint('lavra', __name__)

# Engenharia e cálculos volumétricos (Geometria de Lavra)
def calcular_banco_lavra(comprimento, largura, altura, densidade_material, fator_empolamento):
    metro_cubico_situ = comprimento * largura * altura
    tonelagem_total = metro_cubico_situ * densidade_material
    metro_cubico_solto = metro_cubico_situ * (1.0 + (fator_empolamento / 100.0))

    return {
        'metro_cubico_situ': metro_cubico_situ,
        'tonelagem_total': tonelagem_total,
        'metro_cubico_solto': metro_cubico_solto
    }

@lavra_bp.route('/lavra', methods=['GET', 'POST'])
def lavra():
    if request.method == 'POST':
        comprimento = parse_float(request.form.get('comprimento'), padrao=0.0, minimo=0.0)
        largura = parse_float(request.form.get('largura'), padrao=0.0, minimo=0.0)
        altura = parse_float(request.form.get('altura_banco'), padrao=0.0, minimo=0.0)
        densidade = parse_float(request.form.get('densidade_material'), padrao=2.7, minimo=0.01)
        empolamento = parse_float(request.form.get('fator_empolamento'), padrao=30.0, minimo=0.0)

        nome_frente = request.form.get('nome_frente', '').strip()[:100]
        tipo_material = request.form.get('tipo_material', '').strip()[:100]

        resultado = calcular_banco_lavra(
            comprimento=comprimento,
            largura=largura,
            altura=altura,
            densidade_material=densidade,
            fator_empolamento=empolamento
        )

        dados_lavra = {
            'nome_frente': nome_frente,
            'tipo_material': tipo_material,
            'comprimento': comprimento,
            'largura': largura,
            'altura_banco': altura,
            'densidade_material': densidade,
            'fator_empolamento': empolamento,
            'volume_situ_formatado': formata_numero(resultado['metro_cubico_situ']),
            'tonelagem_formatada': formata_numero(resultado['tonelagem_total']),
            'volume_solto_formatado': formata_numero(resultado['metro_cubico_solto']),
            'volume_situ_raw': resultado['metro_cubico_situ'],
            'tonelagem_raw': resultado['tonelagem_total'],
            'volume_solto_raw': resultado['metro_cubico_solto']
        }

        session['dados_banco'] = dados_lavra
        return render_template('calculos_banco_lavra.html', dados=dados_lavra)

    session.pop('dados_banco', None)
    session.pop('dados_carga', None)
    return render_template('calculos_banco_lavra.html', dados=None)