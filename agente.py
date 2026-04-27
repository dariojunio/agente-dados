import json
import os

from openai import OpenAI

from ferramentas import analisar_dados, executar_pandas, gerar_grafico, _get_df

DEFAULT_MODEL = "gpt-5-mini"


def _get_client() -> OpenAI:
    api_key = None
    try:
        import streamlit as st

        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except Exception:
        api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def _get_model() -> str:
    try:
        import streamlit as st

        return st.secrets.get("OPENAI_MODEL") or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
    except Exception:
        return os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


FERRAMENTAS = [
    {
        "type": "function",
        "name": "analisar_dados",
        "description": "Executa analises exploratorias nos dados ja carregados.",
        "parameters": {
            "type": "object",
            "properties": {
                "operacao": {
                    "type": "string",
                    "enum": ["resumo", "nulos", "tipos", "primeiras_linhas"],
                    "description": "Tipo de analise exploratoria a executar.",
                }
            },
            "required": ["operacao"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "executar_pandas",
        "description": "Executa codigo Python/pandas seguro. Use a variavel df e salve o resultado em resultado.",
        "parameters": {
            "type": "object",
            "properties": {
                "codigo": {
                    "type": "string",
                    "description": "Codigo pandas curto. Nao use imports, arquivos, rede ou atributos internos.",
                }
            },
            "required": ["codigo"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "gerar_grafico",
        "description": "Gera visualizacoes a partir do dataframe carregado.",
        "parameters": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["barras", "linha", "histograma", "pizza", "dispersao", "box"],
                    "description": "Tipo do grafico.",
                },
                "coluna_x": {"type": "string", "description": "Coluna principal do grafico."},
                "coluna_y": {
                    "type": ["string", "null"],
                    "description": "Coluna numerica opcional. Obrigatoria para linha e dispersao.",
                },
                "titulo": {"type": ["string", "null"], "description": "Titulo opcional."},
            },
            "required": ["tipo", "coluna_x", "coluna_y", "titulo"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def executar_ferramenta(nome: str, inputs: dict) -> str:
    if nome == "analisar_dados":
        return analisar_dados(inputs["operacao"])
    if nome == "executar_pandas":
        return executar_pandas(inputs["codigo"])
    if nome == "gerar_grafico":
        return gerar_grafico(
            tipo=inputs["tipo"],
            coluna_x=inputs["coluna_x"],
            coluna_y=inputs.get("coluna_y"),
            titulo=inputs.get("titulo") or "",
        )
    return "Ferramenta nao encontrada."


def _texto_de_blocos(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""

    partes = []
    for bloco in content:
        if isinstance(bloco, dict):
            if bloco.get("type") in {"text", "input_text", "output_text"} and bloco.get("text"):
                partes.append(str(bloco["text"]))
            elif "conteudo" in bloco:
                partes.append(str(bloco["conteudo"]))
        elif hasattr(bloco, "text") and bloco.text:
            partes.append(str(bloco.text))
    return "\n".join(partes).strip()


def _sanitizar_historico(historico: list) -> list:
    """
    Mantem apenas turnos de texto puro para a Responses API.
    Chamadas de ferramenta sao reconstruidas dentro do turno atual.
    """
    resultado = []
    for msg in historico or []:
        role = msg.get("role")
        if role not in {"user", "assistant"}:
            continue

        texto = _texto_de_blocos(msg.get("content"))
        if texto:
            resultado.append({"role": role, "content": texto})

    return _garantir_alternancia(resultado)


def _garantir_alternancia(historico: list) -> list:
    if not historico:
        return historico

    limpo = [historico[0]]
    for msg in historico[1:]:
        ultimo = limpo[-1]
        if msg["role"] == ultimo["role"]:
            limpo[-1] = {
                "role": ultimo["role"],
                "content": f"{ultimo['content']}\n{msg['content']}".strip(),
            }
        else:
            limpo.append(msg)

    return limpo


def _resumo_df() -> str:
    df = _get_df()
    if df is None:
        return "Nenhum arquivo carregado."
    nulos = int(df.isnull().sum().sum())
    colunas_info = [f"  - {col} ({str(df[col].dtype)}, {df[col].nunique()} unicos)" for col in df.columns]
    return (
        f"Arquivo carregado: {df.shape[0]} linhas x {df.shape[1]} colunas. Nulos: {nulos}.\n"
        "Colunas:\n" + "\n".join(colunas_info)
    )


def _extrair_texto_resposta(resposta) -> str:
    texto = getattr(resposta, "output_text", None)
    if texto:
        return texto.strip()

    partes = []
    for item in getattr(resposta, "output", []) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", []) or []:
            if getattr(content, "type", None) in {"output_text", "text"} and getattr(content, "text", None):
                partes.append(content.text)
    return "\n".join(partes).strip()


def _chamadas_de_funcao(resposta) -> list:
    return [
        item
        for item in (getattr(resposta, "output", []) or [])
        if getattr(item, "type", None) == "function_call"
    ]


def rodar_agente(mensagem_usuario: str, historico: list = None) -> tuple:
    if historico is None:
        historico = []

    historico.append({"role": "user", "content": mensagem_usuario})
    artefatos = []
    client = _get_client()

    system_prompt = f"""Voce e um agente especialista em analise de dados. Responda sempre em portugues brasileiro.

ESTADO ATUAL DOS DADOS:
{_resumo_df()}

REGRAS:
- Os dados JA estao carregados. NUNCA peca para o usuario enviar ou carregar arquivo.
- Use as ferramentas diretamente para analisar.
- Gere graficos sempre que a analise for numerica ou comparativa.
- Para graficos de linha e dispersao, informe coluna_y. Para barras, pizza, histograma e box, coluna_y pode ser null.
- Explique resultados em linguagem simples.
- Se nao souber o nome exato de uma coluna, use analisar_dados com operacao='tipos' primeiro.
"""

    input_messages = _sanitizar_historico(historico)

    for _ in range(8):
        resposta = client.responses.create(
            model=_get_model(),
            instructions=system_prompt,
            input=input_messages,
            tools=FERRAMENTAS,
            max_output_tokens=4096,
        )

        chamadas = _chamadas_de_funcao(resposta)
        if not chamadas:
            texto = _extrair_texto_resposta(resposta) or "Analise concluida."
            historico.append({"role": "assistant", "content": texto})
            artefatos.append({"tipo": "texto", "conteudo": texto})
            break

        input_messages.extend(resposta.output)
        for chamada in chamadas:
            try:
                argumentos = json.loads(chamada.arguments or "{}")
            except json.JSONDecodeError:
                argumentos = {}

            resultado = executar_ferramenta(chamada.name, argumentos)
            if resultado.startswith("GRAFICO_BASE64:"):
                artefatos.append({"tipo": "imagem", "conteudo": resultado.replace("GRAFICO_BASE64:", "")})
                resultado = "Grafico gerado com sucesso."

            input_messages.append(
                {
                    "type": "function_call_output",
                    "call_id": chamada.call_id,
                    "output": str(resultado),
                }
            )
    else:
        texto = "A analise foi interrompida porque excedeu o limite de chamadas de ferramenta."
        historico.append({"role": "assistant", "content": texto})
        artefatos.append({"tipo": "texto", "conteudo": texto})

    return historico, artefatos
