import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, session, url_for
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Importação dos módulos operacionais (Blueprints)
from calculos_banco_lavra import lavra_bp
from calculos_operacao_carga import operacao_bp
from calculos_transporte_caminhoes import caminhoes_bp
from planejamento_mensal import planejamento_mensal_app
from dimensionamento_frota import frota_bp
from rotas_maquinas import maquinas_bp
from calculadora_diesel import diesel_bp
from calculadora_britagem import britagem_bp

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mineracore")

try:
    from gerador_pro import gerador_pro_bp
except ImportError as erro_importacao:
    gerador_pro_bp = None
    logger.warning(f"Módulo gerador_pro não carregado: {erro_importacao}")

csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour", "60 per minute"],
    storage_uri="memory://"
)

CHAVES_SESSAO_SIMULACAO = (
    "dados_banco",
    "dados_carga",
    "dados_transporte",
    "dados_planejamento",
    "plano_frota",
    "dados_diesel",
    "resultado_diesel",
)


def create_app() -> Flask:
    app = Flask(__name__)

    is_prod = os.environ.get("FLASK_ENV") == "production"
    secret_key = os.environ.get("SECRET_KEY")

    if is_prod and not secret_key:
        logger.warning("SECRET_KEY não definida em produção; gerando chave temporária.")

    app.secret_key = secret_key or os.urandom(32)

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=is_prod,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,  # 1 MB
    )

    # Inicialização das extensões
    csrf.init_app(app)
    limiter.init_app(app)

    # Registro centralizado dos Blueprints
    blueprints = [
        lavra_bp,
        operacao_bp,
        caminhoes_bp,
        planejamento_mensal_app,
        frota_bp,
        maquinas_bp,
        diesel_bp,
        britagem_bp,
    ]

    if gerador_pro_bp is not None:
        blueprints.append(gerador_pro_bp)

    for bp in blueprints:
        app.register_blueprint(bp)

    # Isenta rotas de API JSON do Handbook IA da verificação CSRF de formulário
    csrf.exempt(maquinas_bp)

    # ---------------------------------------------------------
    # Middlewares de Cabeçalho (Cache e Segurança)
    # ---------------------------------------------------------
    @app.after_request
    def aplicar_cabecalhos_resposta(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    # ---------------------------------------------------------
    # Rotas Principais e Controle de Sessão
    # ---------------------------------------------------------
    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/voltar_dashboard")
    def voltar_dashboard():
        for chave in CHAVES_SESSAO_SIMULACAO:
            session.pop(chave, None)
        return redirect(url_for("dashboard"))

    # ---------------------------------------------------------
    # Rotas de Indexação para Motores de Busca (SEO)
    # ---------------------------------------------------------
    @app.route("/robots.txt")
    @limiter.exempt
    def robots():
        conteudo = (
            "User-agent: *\n"
            "Allow: /\n"
            "Sitemap: https://mineracore.com.br/sitemap.xml"
        )
        return conteudo, 200, {"Content-Type": "text/plain"}

    @app.route("/sitemap.xml")
    @limiter.exempt
    def sitemap():
        url_gerador_pro = (
            "\n    <url><loc>https://mineracore.com.br/gerador-pro</loc><priority>0.8</priority></url>"
            if gerador_pro_bp is not None
            else ""
        )
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://mineracore.com.br/</loc><priority>1.0</priority></url>
    <url><loc>https://mineracore.com.br/dashboard</loc><priority>0.8</priority></url>{url_gerador_pro}
</urlset>"""
        return xml, 200, {"Content-Type": "application/xml"}

    # ---------------------------------------------------------
    # Tratamento Padronizado de Erros
    # ---------------------------------------------------------
    @app.errorhandler(404)
    def pagina_nao_encontrada(erro):
        return redirect(url_for("dashboard"))

    return app


app = create_app()

if __name__ == "__main__":
    is_prod = os.environ.get("FLASK_ENV") == "production"
    app.run(debug=not is_prod)