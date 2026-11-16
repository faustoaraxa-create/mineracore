import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, session, url_for
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from calculos_banco_lavra import lavra_bp
from calculos_operacao_carga import operacao_bp
from calculos_transporte_caminhoes import caminhoes_bp
from planejamento_mensal import planejamento_mensal_app
from rotas_maquinas import maquinas_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(32)

is_prod = os.environ.get('FLASK_ENV') == 'production'
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=is_prod,
    SESSION_COOKIE_SAMESITE='Lax',
    MAX_CONTENT_LENGTH=1 * 1024 * 1024
)

csrf = CSRFProtect(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour", "60 per minute"],
    storage_uri="memory://"
)

# Registro dos módulos (Blueprints)
app.register_blueprint(lavra_bp)
app.register_blueprint(operacao_bp)
app.register_blueprint(caminhoes_bp)
app.register_blueprint(planejamento_mensal_app)
app.register_blueprint(maquinas_bp)

# Isenta a API JSON do Handbook de verificação CSRF de formulário
csrf.exempt(maquinas_bp)

# ---------------------------------------------------------
# Controle de Cache Profissional (Impede dados presos ao voltar)
# ---------------------------------------------------------
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# Rota para limpar os dados da sessão ao sair do dimensionamento
@app.route("/voltar_dashboard")
def voltar_dashboard():
    session.pop('dados_banco', None)
    session.pop('dados_carga', None)
    session.pop('dados_transporte', None)
    session.pop('dados_planejamento', None)
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    app.run(debug=not is_prod)