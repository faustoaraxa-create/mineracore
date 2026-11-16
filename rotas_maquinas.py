from flask import Blueprint, render_template, request, jsonify
from buscador_maquinas import buscar_especificacoes_maquina

maquinas_bp = Blueprint("maquinas", __name__)

CATEGORIAS_MAQUINAS = {
    "escavadeira": {
        "titulo": "Escavadeiras Hidráulicas",
        "descricao": "Escavadeiras sobre esteiras para carregamento, abertura de frentes e escavação pesada.",
        "icone": "🚜",
        "label_implemento": "Capacidade da Caçamba",
        "label_dimensao": "Parâmetro Operacional",
        "placeholder_marca": "Ex: Caterpillar, Komatsu, Hitachi, Volvo",
        "placeholder_modelo": "Ex: 320, PC200, EX1200-7, EC220D",
        "catalogo": {
            "Caterpillar": ["320", "336", "349", "374", "395", "6015B"],
            "Komatsu": ["PC200", "PC350", "PC490", "PC800", "PC1250", "PC2000"],
            "Hitachi": ["ZX210", "ZX350", "ZX490", "EX1200-7", "EX2600-7"],
            "Volvo": ["EC220D", "EC350D", "EC480D", "EC750E", "EC950F"],
            "Liebherr": ["R 922", "R 938", "R 956", "R 9150", "R 9200"],
            "John Deere": ["210G", "350G", "470G", "670G", "870G"],
            "Sany": ["SY215C", "SY365H", "SY500H", "SY750H"]
        }
    },
    "pa-carregadeira": {
        "titulo": "Pás Carregadeiras",
        "descricao": "Carregadeiras de rodas para alimentação de britadores, pilhas de estoque e carregamento de caminhões.",
        "icone": "🏗️",
        "label_implemento": "Capacidade da Caçamba",
        "label_dimensao": "Parâmetro Operacional",
        "placeholder_marca": "Ex: Caterpillar, Volvo, Komatsu, XCMG",
        "placeholder_modelo": "Ex: 966, 980, L120H, WA470",
        "catalogo": {
            "Caterpillar": ["950", "966", "972", "980", "988K", "992"],
            "Volvo": ["L90H", "L120H", "L150H", "L180H", "L220H", "L350H"],
            "Komatsu": ["WA320", "WA380", "WA470", "WA500", "WA600", "WA900"],
            "John Deere": ["624L", "644L", "724L", "824L", "844L"],
            "Case": ["621F", "721F", "821F", "921F", "1021F"],
            "XCMG": ["LW300KV", "LW500KV", "LW600KV", "LW800KV"]
        }
    },
    "trator": {
        "titulo": "Tratores de Esteiras",
        "descricao": "Bulldozers para decapeamento, abertura de acessos, manutenção de praças e pilhas de estéril.",
        "icone": "⚙️",
        "label_implemento": "Capacidade da Lâmina",
        "label_dimensao": "Parâmetro Operacional",
        "placeholder_marca": "Ex: Caterpillar, Komatsu, John Deere",
        "placeholder_modelo": "Ex: D6, D8T, D10T, D65EX, D155AX",
        "catalogo": {
            "Caterpillar": ["D5", "D6", "D7", "D8T", "D9T", "D10T", "D11"],
            "Komatsu": ["D51EX", "D61EX", "D65EX", "D85EX", "D155AX", "D375A"],
            "John Deere": ["700K", "750K", "850K", "950K", "1050K"],
            "Liebherr": ["PR 726", "PR 736", "PR 756", "PR 766", "PR 776"],
            "Case": ["1150M", "1650M", "2050M"]
        }
    },
    "motoniveladora": {
        "titulo": "Motoniveladoras",
        "descricao": "Patrols para conformação e manutenção de estradas de mina, praças de carga e drenagem.",
        "icone": "🛣️",
        "label_implemento": "Largura da Lâmina",
        "label_dimensao": "Parâmetro Operacional",
        "placeholder_marca": "Ex: Caterpillar, John Deere, Volvo, Komatsu",
        "placeholder_modelo": "Ex: 140K, 14M, 16M, 670G, GD655",
        "catalogo": {
            "Caterpillar": ["120", "140K", "140", "14M", "16M", "18", "24"],
            "John Deere": ["620G", "670G", "770G", "870G"],
            "Komatsu": ["GD555", "GD655", "GD675", "GD825A"],
            "Volvo": ["G930", "G940", "G960", "G990"],
            "Case": ["845B", "865B", "885B"]
        }
    },
    "retroescavadeira": {
        "titulo": "Retroescavadeiras",
        "descricao": "Equipamentos versáteis para serviços auxiliares, valas, drenagem e apoio operacional.",
        "icone": "🛠️",
        "label_implemento": "Capacidade da Caçamba",
        "label_dimensao": "Parâmetro Operacional",
        "placeholder_marca": "Ex: JCB, Caterpillar, Case, John Deere",
        "placeholder_modelo": "Ex: 3CX, 4CX, 416F2, 580N, 310L",
        "catalogo": {
            "JCB": ["3CX", "4CX", "5CX"],
            "Caterpillar": ["416", "416F2", "420", "426", "432"],
            "Case": ["580N", "580SN", "590SN"],
            "John Deere": ["310L", "310SL", "410L", "710L"],
            "New Holland": ["B95B", "B110B", "B115B"]
        }
    }
}


@maquinas_bp.route("/maquinas")
def index_maquinas():
    return render_template("maquinas.html", categorias=CATEGORIAS_MAQUINAS)


@maquinas_bp.route("/maquinas/<categoria>")
def consulta_categoria(categoria: str):
    cat_key = categoria.strip().lower()
    if cat_key not in CATEGORIAS_MAQUINAS:
        return render_template("maquinas.html", categorias=CATEGORIAS_MAQUINAS)

    info = CATEGORIAS_MAQUINAS[cat_key]
    return render_template(
        "consulta_maquina.html",
        categoria=cat_key,
        categoria_key=cat_key,
        info=info,
        catalogo=info.get("catalogo", {})
    )


@maquinas_bp.route("/api/buscar-maquina", methods=["POST"])
def api_buscar_maquina():
    dados = request.get_json(silent=True) or {}
    categoria = (dados.get("categoria") or "").strip().lower()
    marca = (dados.get("marca") or "").strip()
    modelo = (dados.get("modelo") or "").strip()

    if not categoria or not marca or not modelo:
        return jsonify({
            "sucesso": False,
            "erro": "Informe a categoria, a marca e o modelo do equipamento."
        }), 400

    if categoria not in CATEGORIAS_MAQUINAS:
        return jsonify({
            "sucesso": False,
            "erro": f"Categoria '{categoria}' inválida."
        }), 400

    resultado = buscar_especificacoes_maquina(categoria, marca, modelo)
    if "erro" in resultado:
        return jsonify({
            "sucesso": False,
            "erro": resultado["erro"]
        }), 400

    origem = resultado.pop("_origem", "api")
    return jsonify({
        "sucesso": True,
        "origem": origem,
        "dados": resultado
    }), 200