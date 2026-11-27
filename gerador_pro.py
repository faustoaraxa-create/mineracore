from flask import Blueprint, render_template

gerador_pro_bp = Blueprint("gerador_pro", __name__)


@gerador_pro_bp.route("/gerador-pro")
def exibir_gerador_pro():
    return render_template("gerador_pro.html")