import os
import anthropic

def _get_client():
    api_key = None
    try:
        import streamlit as st
        api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    except Exception:
        api_key = os.getenv("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=api_key)

from ferramentas import carregar_arquivo, analisar_dados, executar_pandas, gerar_grafico, _get_df

FERRAMENTAS = [
    {
        "name": "analisar_dados",
        "description": "Executa análises exploratórias nos dados já carregados. Use isso antes de responder perguntas sobre os dados.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operacao": {
                    "type": "string",
                    "enum": ["resumo", "nulos", "tipos", "primeiras_linhas"],
                    "description": "resumo: estatísticas descritivas | nulos: valores ausentes | tipos: tipos de dados | primeiras_linhas: preview"
                }
            },
            "required": ["operacao"]
        }
    },
    {
        "name": "executar_pandas",
        "description": "Executa código Python/pandas para análises customizadas. Use a variável 'df' e salve o resultado em 'resultado'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "codigo": {
                    "type": "string",
                    "description": "Ex: resultado = df.groupby('categoria')['vendas'].sum().to_string()"
                }
            },
            "required": ["codigo"]
        }
    },
    {
        "name": "gerar_grafico",
        "description": "Gera visualizações. Sempre gere um gráfico após análises numéricas relevantes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["barras", "linha", "histograma", "pizza", "dispersao", "box"]
                },
                "coluna_x": {"type": "string", "description": "Coluna principal ou eixo X"},
                "coluna_y": {"type": "string", "description": "Eixo Y (obrigatório para barras, linha, dispersao)"},
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

def _resumo_df() -> str:
    """Gera um resumo do dataframe atual para incluir no system prompt."""
    df = _get_df()
    if df is None:
        return "Nenhum arquivo carregado."
    nulos = int(df.isnull().sum().sum())
    colunas_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        n_uniq = df[col].nunique()
        colunas_info.append(f"  - {col} ({dtype}, {n_uniq} únicos)")
    return (
        f"Arquivo carregado: {df.shape[0]} linhas x {df.shape[1]} colunas. "
        f"Valores nulos: {nulos}.\n"
        f"Colunas:\n" + "\n".join(colunas_info)
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

REGRAS IMPORTANTES:
- Os dados JÁ estão carregados. NUNCA peça para o usuário carregar um arquivo ou enviar dados novamente.
- Use as ferramentas diretamente para analisar — não peça confirmação antes.
- Gere gráficos sempre que a análise for numérica ou comparativa.
- Explique os resultados em linguagem simples e direta.
- Se não souber o nome exato de uma coluna, use analisar_dados com operacao='tipos' para descobrir.
"""

    while True:
        resposta = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=system_prompt,
            tools=FERRAMENTAS,
            messages=historico
        )

        if resposta.stop_reason == "end_turn":
            historico.append({"role": "assistant", "content": resposta.content})
            for bloco in resposta.content:
                if hasattr(bloco, "text"):
                    artefatos.append({"tipo": "texto", "conteudo": bloco.text})
            break

        if resposta.stop_reason == "tool_use":
            historico.append({"role": "assistant", "content": resposta.content})
            resultados = []
            for bloco in resposta.content:
                if bloco.type == "tool_use":
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
