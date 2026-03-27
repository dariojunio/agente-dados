import os
import json
import anthropic

def _get_client():
    api_key = None
    try:
        import streamlit as st
        api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    except Exception:
        api_key = os.getenv("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=api_key)

from ferramentas import analisar_dados, executar_pandas, gerar_grafico, _get_df

FERRAMENTAS = [
    {
        "name": "analisar_dados",
        "description": "Executa análises exploratórias nos dados já carregados.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operacao": {
                    "type": "string",
                    "enum": ["resumo", "nulos", "tipos", "primeiras_linhas"]
                }
            },
            "required": ["operacao"]
        }
    },
    {
        "name": "executar_pandas",
        "description": "Executa código Python/pandas. Use a variável 'df' e salve o resultado em 'resultado'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "codigo": {"type": "string"}
            },
            "required": ["codigo"]
        }
    },
    {
        "name": "gerar_grafico",
        "description": "Gera visualizações. Sempre gere um gráfico após análises numéricas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["barras", "linha", "histograma", "pizza", "dispersao", "box"]
                },
                "coluna_x": {"type": "string"},
                "coluna_y": {"type": "string"},
                "titulo": {"type": "string"}
            },
            "required": ["tipo", "coluna_x"]
        }
    }
]

def executar_ferramenta(nome: str, inputs: dict) -> str:
    if nome == "analisar_dados":
        return analisar_dados(inputs["operacao"])
    elif nome == "executar_pandas":
        return executar_pandas(inputs["codigo"])
    elif nome == "gerar_grafico":
        return gerar_grafico(
            tipo=inputs["tipo"],
            coluna_x=inputs["coluna_x"],
            coluna_y=inputs.get("coluna_y"),
            titulo=inputs.get("titulo", "")
        )
    return "Ferramenta não encontrada."

def _sanitizar_historico(historico: list) -> list:
    """
    Garante que o histórico é 100% JSON puro antes de enviar para a API.
    Remove objetos Python da Anthropic que podem ter vazado para o session_state.
    """
    resultado = []
    for msg in historico:
        role = msg["role"]
        content = msg["content"]

        if isinstance(content, str):
            if content.strip():  # ignora strings vazias
                resultado.append({"role": role, "content": content})
            continue

        if isinstance(content, list):
            blocos = []
            for bloco in content:
                if isinstance(bloco, dict):
                    t = bloco.get("type", "")
                    if t == "text":
                        texto = bloco.get("text", "")
                        if texto:  # ignora blocos de texto vazios
                            blocos.append({"type": "text", "text": texto})
                    elif t == "tool_use":
                        blocos.append({
                            "type": "tool_use",
                            "id": bloco["id"],
                            "name": bloco["name"],
                            "input": bloco["input"]
                        })
                    elif t == "tool_result":
                        blocos.append({
                            "type": "tool_result",
                            "tool_use_id": bloco["tool_use_id"],
                            "content": bloco["content"]
                        })
                elif hasattr(bloco, "type"):
                    t = bloco.type
                    if t == "text" and bloco.text:
                        blocos.append({"type": "text", "text": bloco.text})
                    elif t == "tool_use":
                        blocos.append({
                            "type": "tool_use",
                            "id": bloco.id,
                            "name": bloco.name,
                            "input": bloco.input
                        })

            # FIX: nunca adiciona mensagem com content vazio — isso causa
            # BadRequestError ou quebra a alternância user/assistant.
            # Se não sobrou nenhum bloco reconhecido, usa um placeholder.
            if not blocos:
                if role == "assistant":
                    blocos = [{"type": "text", "text": "..."}]
                else:
                    # mensagem user sem conteúdo válido: descarta com segurança
                    continue

            resultado.append({"role": role, "content": blocos})

    # Garante alternância correta user/assistant.
    # Remove mensagens duplicadas consecutivas do mesmo role para evitar 400.
    resultado = _garantir_alternancia(resultado)

    return resultado


def _garantir_alternancia(historico: list) -> list:
    """
    A API exige que as mensagens alternem entre user e assistant.
    Se houver dois user ou dois assistant seguidos (por bug ou edge case),
    mescla os blocos no primeiro para não perder contexto.
    """
    if not historico:
        return historico

    limpo = [historico[0]]
    for msg in historico[1:]:
        ultimo = limpo[-1]
        if msg["role"] == ultimo["role"]:
            # Mesmo role: mescla os blocos na mensagem anterior
            content_anterior = ultimo["content"]
            content_novo = msg["content"]
            if isinstance(content_anterior, list) and isinstance(content_novo, list):
                limpo[-1] = {"role": ultimo["role"], "content": content_anterior + content_novo}
            elif isinstance(content_anterior, str) and isinstance(content_novo, str):
                limpo[-1] = {"role": ultimo["role"], "content": content_anterior + "\n" + content_novo}
            # outros casos: mantém o existente e descarta o duplicado
        else:
            limpo.append(msg)

    return limpo


def _resumo_df() -> str:
    df = _get_df()
    if df is None:
        return "Nenhum arquivo carregado."
    nulos = int(df.isnull().sum().sum())
    colunas_info = [f"  - {col} ({str(df[col].dtype)}, {df[col].nunique()} únicos)" for col in df.columns]
    return (
        f"Arquivo carregado: {df.shape[0]} linhas x {df.shape[1]} colunas. Nulos: {nulos}.\n"
        "Colunas:\n" + "\n".join(colunas_info)
    )

def rodar_agente(mensagem_usuario: str, historico: list = None) -> tuple:
    if historico is None:
        historico = []

    historico.append({"role": "user", "content": mensagem_usuario})
    artefatos = []
    client = _get_client()

    system_prompt = f"""Você é um agente especialista em análise de dados. Responda sempre em português brasileiro.

ESTADO ATUAL DOS DADOS:
{_resumo_df()}

REGRAS:
- Os dados JÁ estão carregados. NUNCA peça para o usuário enviar ou carregar arquivo.
- Use as ferramentas diretamente para analisar.
- Gere gráficos sempre que a análise for numérica ou comparativa.
- Explique resultados em linguagem simples.
- Se não souber o nome exato de uma coluna, use analisar_dados com operacao='tipos' primeiro.
"""

    while True:
        # Sanitiza o histórico antes de cada chamada à API
        historico_limpo = _sanitizar_historico(historico)

        resposta = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=system_prompt,
            tools=FERRAMENTAS,
            messages=historico_limpo
        )

        if resposta.stop_reason == "end_turn":
            blocos_limpos = []
            for bloco in resposta.content:
                if hasattr(bloco, "text") and bloco.text:
                    blocos_limpos.append({"type": "text", "text": bloco.text})
                    artefatos.append({"tipo": "texto", "conteudo": bloco.text})

            # FIX: garante que o assistant nunca entre no histórico com content=[].
            # Content vazio causa o sanitizador a descartar a mensagem, deixando
            # duas mensagens user seguidas e gerando BadRequestError na próxima chamada.
            if not blocos_limpos:
                blocos_limpos = [{"type": "text", "text": "Análise concluída."}]

            historico.append({"role": "assistant", "content": blocos_limpos})
            break

        if resposta.stop_reason == "tool_use":
            # Guarda blocos do assistente como dicts puros
            blocos_assistente = []
            tool_uses = []
            for bloco in resposta.content:
                if bloco.type == "text":
                    blocos_assistente.append({"type": "text", "text": bloco.text})
                elif bloco.type == "tool_use":
                    blocos_assistente.append({
                        "type": "tool_use",
                        "id": bloco.id,
                        "name": bloco.name,
                        "input": bloco.input
                    })
                    tool_uses.append(bloco)

            historico.append({"role": "assistant", "content": blocos_assistente})

            # Executa ferramentas e guarda resultados
            resultados = []
            for bloco in tool_uses:
                resultado = executar_ferramenta(bloco.name, bloco.input)
                if resultado.startswith("GRAFICO_BASE64:"):
                    artefatos.append({"tipo": "imagem", "conteudo": resultado.replace("GRAFICO_BASE64:", "")})
                    resultado = "Gráfico gerado com sucesso."
                resultados.append({
                    "type": "tool_result",
                    "tool_use_id": bloco.id,
                    "content": resultado
                })

            historico.append({"role": "user", "content": resultados})

    return historico, artefatos
