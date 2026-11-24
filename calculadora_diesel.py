import math
from flask import Blueprint, render_template, request, session, redirect, url_for

diesel_bp = Blueprint("diesel_bp", __name__)


class CalculadoraConsumoDiesel:
    """
    Calcula o consumo horário, volume total, autonomia útil e custo de diesel
    para equipamentos individuais e consolida frotas completas de lavra.
    """

    CONSUMO_ESPECIFICO_PADRAO = 0.22  # Litros por HP·hora
    RESERVA_SEGURANCA_TANQUE = 0.40   # Reserva operacional recomendada de 40%
    FATOR_UTILIZACAO_TANQUE = 0.60    # 60% de volume útil consumido entre paradas

    def __init__(
        self,
        equipamento: str,
        quantidade: int,
        potencia_hp: float,
        fator_carga: float,
        consumo_manual: float,
        horas_operacao: float,
        capacidade_tanque: float,
        preco_diesel: float,
    ):
        self.equipamento = equipamento
        self.quantidade = max(1, quantidade)
        self.potencia_hp = max(0.0, potencia_hp)
        self.fator_carga = max(0.0, fator_carga)
        self.consumo_manual = max(0.0, consumo_manual)
        self.horas_operacao = max(0.0, horas_operacao)
        self.capacidade_tanque = max(0.0, capacidade_tanque)
        self.preco_diesel = max(0.0, preco_diesel)

    @staticmethod
    def formatar_br(valor: float, casas: int = 2) -> str:
        texto = f"{valor:,.{casas}f}"
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")

    def calcular_consumo_unitario_lh(self) -> float:
        if self.consumo_manual > 0:
            return self.consumo_manual
        return self.potencia_hp * self.fator_carga * self.CONSUMO_ESPECIFICO_PADRAO

    def gerar_item_frota(self) -> dict:
        """Retorna os valores numéricos brutos e formatados de um item da frota."""
        consumo_unitario_lh = self.calcular_consumo_unitario_lh()
        consumo_grupo_lh = consumo_unitario_lh * self.quantidade
        litros_totais = consumo_grupo_lh * self.horas_operacao

        custo_hora = consumo_grupo_lh * self.preco_diesel
        custo_total = litros_totais * self.preco_diesel

        if self.consumo_manual > 0:
            regime_texto = "Manual"
        else:
            regime_texto = f"{int(round(self.fator_carga * 100))}%"

        if consumo_unitario_lh > 0 and self.capacidade_tanque > 0:
            volume_util_abastecimento = self.capacidade_tanque * self.FATOR_UTILIZACAO_TANQUE
            volume_reserva = self.capacidade_tanque * self.RESERVA_SEGURANCA_TANQUE
            autonomia_horas = volume_util_abastecimento / consumo_unitario_lh
            qtd_abastecimentos = max(0, math.ceil((self.horas_operacao / autonomia_horas) - 1))
        else:
            volume_util_abastecimento = 0.0
            volume_reserva = 0.0
            autonomia_horas = 0.0
            qtd_abastecimentos = 0

        return {
            # Valores numéricos puros para soma consolidada na sessão
            "equipamento": self.equipamento,
            "quantidade": self.quantidade,
            "potencia_hp": self.potencia_hp,
            "regime_texto": regime_texto,
            "horas_operacao": self.horas_operacao,
            "capacidade_tanque": self.capacidade_tanque,
            "preco_diesel": self.preco_diesel,
            "consumo_unitario_lh_num": consumo_unitario_lh,
            "consumo_grupo_lh_num": consumo_grupo_lh,
            "litros_totais_num": litros_totais,
            "custo_hora_num": custo_hora,
            "custo_total_num": custo_total,
            "volume_abastecimento_num": volume_util_abastecimento,
            "volume_reserva_num": volume_reserva,
            # Valores formatados para exibição na tabela HTML
            "consumo_unitario_lh": self.formatar_br(consumo_unitario_lh, 2),
            "consumo_grupo_lh": self.formatar_br(consumo_grupo_lh, 2),
            "litros_totais": self.formatar_br(litros_totais, 2),
            "custo_total": self.formatar_br(custo_total, 2),
            "autonomia_horas": self.formatar_br(autonomia_horas, 1),
            "qtd_abastecimentos": qtd_abastecimentos,
            "volume_abastecimento": self.formatar_br(volume_util_abastecimento, 0),
        }

    @classmethod
    def consolidar_frota(cls, lista_itens: list, produtividade_th: float = 0.0) -> dict | None:
        """Soma todos os equipamentos cadastrados na frente e calcula os KPIs globais."""
        if not lista_itens:
            return None

        total_maquinas = sum(item["quantidade"] for item in lista_itens)
        consumo_frota_lh = sum(item["consumo_grupo_lh_num"] for item in lista_itens)
        litros_totais = sum(item["litros_totais_num"] for item in lista_itens)
        custo_hora = sum(item["custo_hora_num"] for item in lista_itens)
        custo_total = sum(item["custo_total_num"] for item in lista_itens)
        total_paradas_comboio = sum(item["qtd_abastecimentos"] * item["quantidade"] for item in lista_itens)

        if produtividade_th > 0 and consumo_frota_lh > 0:
            litros_por_ton = cls.formatar_br(consumo_frota_lh / produtividade_th, 3)
            custo_por_ton = cls.formatar_br(custo_hora / produtividade_th, 2)
        else:
            litros_por_ton = None
            custo_por_ton = None

        return {
            "total_grupos": len(lista_itens),
            "total_maquinas": total_maquinas,
            "consumo_frota_lh": cls.formatar_br(consumo_frota_lh, 2),
            "litros_totais": cls.formatar_br(litros_totais, 2),
            "custo_hora": cls.formatar_br(custo_hora, 2),
            "custo_total": cls.formatar_br(custo_total, 2),
            "total_paradas_comboio": total_paradas_comboio,
            "litros_por_ton": litros_por_ton,
            "custo_por_ton": custo_por_ton,
            "produtividade_th": cls.formatar_br(produtividade_th, 1) if produtividade_th > 0 else "",
        }


def _ler_float(campo: str, padrao: float = 0.0) -> float:
    valor_bruto = request.form.get(campo, "").strip().replace(",", ".")
    if not valor_bruto:
        return padrao
    try:
        return float(valor_bruto)
    except ValueError:
        return padrao


@diesel_bp.route("/consumo_diesel", methods=["GET", "POST"])
def consumo_diesel():
    lista_frota = session.get("lista_frota_diesel", [])
    produtividade_salva = session.get("produtividade_diesel_th", 0.0)
    ultimo_preco = session.get("ultimo_preco_diesel", 6.15)
    ultimas_horas = session.get("ultimas_horas_diesel", 12.0)

    if request.method == "POST":
        acao = request.form.get("acao", "adicionar")

        # Atualiza apenas a produtividade global da frente sem precisar cadastrar máquina
        if acao == "atualizar_producao":
            produtividade_salva = _ler_float("produtividade_global", 0.0)
            session["produtividade_diesel_th"] = produtividade_salva
        else:
            equipamento = request.form.get("equipamento", "").strip()
            quantidade = int(_ler_float("quantidade", 1))
            potencia_hp = _ler_float("potencia_hp", 0.0)
            fator_carga = _ler_float("fator_carga", 0.50)
            consumo_manual = _ler_float("consumo_manual", 0.0)
            horas_operacao = _ler_float("horas_operacao", 12.0)
            capacidade_tanque = _ler_float("capacidade_tanque", 600.0)
            preco_diesel = _ler_float("preco_diesel", 6.15)
            prod_form = _ler_float("producao_ton", 0.0)

            if prod_form > 0:
                produtividade_salva = prod_form
                session["produtividade_diesel_th"] = produtividade_salva

            session["ultimo_preco_diesel"] = preco_diesel
            session["ultimas_horas_diesel"] = horas_operacao
            ultimo_preco = preco_diesel
            ultimas_horas = horas_operacao

            if equipamento and (potencia_hp > 0 or consumo_manual > 0):
                calc = CalculadoraConsumoDiesel(
                    equipamento=equipamento,
                    quantidade=quantidade,
                    potencia_hp=potencia_hp,
                    fator_carga=fator_carga,
                    consumo_manual=consumo_manual,
                    horas_operacao=horas_operacao,
                    capacidade_tanque=capacidade_tanque,
                    preco_diesel=preco_diesel,
                )
                lista_frota.append(calc.gerar_item_frota())
                session["lista_frota_diesel"] = lista_frota

    consolidado = CalculadoraConsumoDiesel.consolidar_frota(lista_frota, produtividade_salva)

    return render_template(
        "consumo_diesel.html",
        lista_frota=lista_frota,
        consolidado=consolidado,
        produtividade_th=produtividade_salva if produtividade_salva > 0 else "",
        ultimo_preco=ultimo_preco,
        ultimas_horas=ultimas_horas,
    )


@diesel_bp.route("/remover_item_diesel/<int:indice>", methods=["POST"])
def remover_item_diesel(indice: int):
    lista_frota = session.get("lista_frota_diesel", [])
    if 0 <= indice < len(lista_frota):
        lista_frota.pop(indice)
        session["lista_frota_diesel"] = lista_frota
    return redirect(url_for("diesel_bp.consumo_diesel"))


@diesel_bp.route("/limpar_diesel")
def limpar_diesel():
    session.pop("lista_frota_diesel", None)
    session.pop("produtividade_diesel_th", None)
    session.pop("dados_diesel", None)
    session.pop("resultado_diesel", None)
    return redirect(url_for("diesel_bp.consumo_diesel"))