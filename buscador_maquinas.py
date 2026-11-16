import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

ARQUIVO_CACHE = Path(__file__).resolve().parent / "cache_maquinas.json"
MODELOS_GEMINI = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]

CONTEXTO_CATEGORIAS = {
    "escavadeira": {
        "nome_tecnico": "Escavadeira Hidráulica (Hydraulic Excavator)",
        "label_capacidade": "Capacidade da Caçamba",
        "label_parametro": "Profundidade Máx. de Escavação",
        "exemplo_capacidade": "Ex: 1,19 m³ a 2,40 m³",
        "exemplo_parametro": "Ex: 6.720 mm"
    },
    "pa-carregadeira": {
        "nome_tecnico": "Pá Carregadeira de Rodas (Wheel Loader)",
        "label_capacidade": "Capacidade da Caçamba",
        "label_parametro": "Carga de Tombamento / Altura de Descarga",
        "exemplo_capacidade": "Ex: 4,20 m³ a 5,70 m³",
        "exemplo_parametro": "Ex: Carga tombamento 19.500 kg"
    },
    "trator": {
        "nome_tecnico": "Trator de Esteiras (Track-Type Tractor / Bulldozer)",
        "label_capacidade": "Capacidade da Lâmina",
        "label_parametro": "Tipo de Lâmina / Ripper",
        "exemplo_capacidade": "Ex: 8,70 m³ (Lâmina SU)",
        "exemplo_parametro": "Ex: Lâmina Semi-U + Ripper 3 dentes"
    },
    "motoniveladora": {
        "nome_tecnico": "Motoniveladora (Motor Grader)",
        "label_capacidade": "Largura da Lâmina",
        "label_parametro": "Tração / Peso no Eixo Traseiro",
        "exemplo_capacidade": "Ex: 4,27 m (14 pés)",
        "exemplo_parametro": "Ex: Tração Tandem 6x4"
    },
    "retroescavadeira": {
        "nome_tecnico": "Retroescavadeira (Backhoe Loader)",
        "label_capacidade": "Capacidade da Caçamba Frontal / Retro",
        "label_parametro": "Profundidade Máx. de Escavação",
        "exemplo_capacidade": "Ex: 1,00 m³ frontal / 0,24 m³ retro",
        "exemplo_parametro": "Ex: 4.360 mm"
    }
}


class FichaTecnicaMaquina(BaseModel):
    marca: str = Field(description="Nome oficial padronizado do fabricante (ex: Caterpillar, Komatsu, John Deere).")
    modelo: str = Field(description="Código oficial padronizado do modelo (ex: 336, PC200, 210G).")
    peso_operacional: str = Field(description="Peso operacional em kg ou toneladas (ex: '36.800 kg (36,8 t)').")
    potencia_liquida: str = Field(description="Potência líquida do motor em HP e kW (ex: '311 HP (232 kW)').")
    capacidade: str = Field(description="Capacidade ou largura do implemento principal conforme a categoria.")
    parametro_operacional: str = Field(description="Principal parâmetro dimensional ou operacional da categoria.")
    fonte_nome: str = Field(description="Nome da documentação técnica de referência (ex: 'Catálogo Técnico Oficial Caterpillar').")
    fonte_url: Optional[str] = Field(default=None, description="URL oficial do fabricante se conhecida, ou null.")


def _carregar_cache() -> dict:
    if not ARQUIVO_CACHE.exists():
        return {}
    try:
        with open(ARQUIVO_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_cache(cache: dict) -> None:
    try:
        with open(ARQUIVO_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[MineraCore Cache] Aviso ao salvar cache: {e}")


def _gerar_chave_cache(categoria: str, marca: str, modelo: str) -> str:
    cat = categoria.strip().lower()
    m = "".join(marca.strip().lower().split())
    mod = "".join(modelo.strip().lower().split())
    return f"{cat}:{m}:{mod}"


def _buscar_snippet_web(query: str) -> str:
    if DDGS is None:
        return ""
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=3))
        trechos = [f"- {r.get('title', '')}: {r.get('body', '')}" for r in resultados]
        return "\n".join(trechos)
    except Exception:
        return ""


def buscar_especificacoes_maquina(categoria: str, marca: str, modelo: str) -> dict:
    chave = _gerar_chave_cache(categoria, marca, modelo)
    cache = _carregar_cache()

    if chave in cache:
        dados_cache = dict(cache[chave])
        dados_cache["_origem"] = "cache"
        return dados_cache

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {"erro": "Chave GEMINI_API_KEY não configurada no ambiente (.env)."}

    ctx = CONTEXTO_CATEGORIAS.get(categoria, {
        "nome_tecnico": categoria,
        "label_capacidade": "Capacidade",
        "label_parametro": "Parâmetro Operacional",
        "exemplo_capacidade": "Ex: 3,0 m³",
        "exemplo_parametro": "Ex: Padrão de fábrica"
    })

    # Busca snippet complementar rápido apenas para reforçar modelos menos comuns
    query_web = f"{marca} {modelo} {ctx['nome_tecnico']} operating weight net power specifications"
    contexto_web = _buscar_snippet_web(query_web)

    prompt = f"""
Você é um engenheiro especialista em equipamentos pesados de mineração e terraplenagem.
Forneça a ficha técnica oficial (especificações padrão de fábrica) do seguinte equipamento:

- Categoria: {ctx['nome_tecnico']}
- Fabricante / Marca: {marca}
- Modelo: {modelo}

Regras obrigatórias:
1. Use valores reais de catálogo técnico oficial do fabricante (sistema métrico: kg ou t, HP e kW, m³ ou m).
2. No campo 'capacidade', informe o valor referente a: {ctx['label_capacidade']} ({ctx['exemplo_capacidade']}).
3. No campo 'parametro_operacional', informe o valor referente a: {ctx['label_parametro']} ({ctx['exemplo_parametro']}).
4. Nunca deixe campos em branco ou 'N/A' se o equipamento existir na linha industrial/mineração; forneça o valor padrão da configuração base do modelo.
5. Se não tiver certeza absoluta da URL direta da ficha, retorne fonte_url como null (nunca invente links quebrados).

Trechos auxiliares da web (use apenas se forem consistentes com o modelo exato):
{contexto_web if contexto_web else "Sem trechos adicionais."}
""".strip()

    client = genai.Client(api_key=api_key)
    ultimo_erro = None

    for nome_modelo in MODELOS_GEMINI:
        try:
            response = client.models.generate_content(
                model=nome_modelo,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=FichaTecnicaMaquina,
                    temperature=0.1,
                ),
            )

            texto_json = (response.text or "").strip()
            if not texto_json:
                raise ValueError("Resposta vazia do modelo.")

            dados_validados = FichaTecnicaMaquina.model_validate_json(texto_json).model_dump()
            dados_validados["label_capacidade"] = ctx["label_capacidade"]
            dados_validados["label_parametro"] = ctx["label_parametro"]

            cache[chave] = dados_validados
            _salvar_cache(cache)

            resultado = dict(dados_validados)
            resultado["_origem"] = "api"
            return resultado

        except Exception as e:
            ultimo_erro = str(e)
            continue

    return {"erro": f"Não foi possível obter os dados técnicos de {marca} {modelo}. ({ultimo_erro})"}