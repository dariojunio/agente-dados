import anthropic
import json
from ferramentas import carregar_arquivo, analisar_dados, executar_pandas, gerar_grafico

client = anthropic.Anthropic()  # pega a chave de ANTHROPIC_API_KEY no ambiente

FERRAMENTAS = [
    {
        "name": "carregar_arquivo",
        "description": "Carrega um arquivo CSV ou Excel para análise. Retorna informações sobre as colunas e tipos de dados.",
        "input_schema": {
            "type": "object",
            "properties": {
                "caminho": {
                    "type": "string",
                    "description": "Caminho do arquivo. Ex: dados.csv ou dados.xlsx"
                }
            },
            "required": ["caminho"]
        }
    },
    {
        "name": "analisar_dados",
        "description": "Executa análises exploratórias básicas: resumo estatístico, valores nulos, tipos de dados e primeiras linhas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operacao": {
                    "type": "string",
                    "enum": ["resumo", "nulos", "tipos", "primeiras_linhas"],
                    "description": "resumo: estatísticas descritivas | nulos: colunas com valores ausentes | tipos: tipos de dados | primeiras_linhas: preview dos dados"
                }
            },
            "required": ["operacao"]
        }
    },
    {
        "name": "executar_pandas",
        "description": "Executa código Python/pandas para análises customizadas. Use a variável 'df' para acessar os dados e salve o resultado na variável 'resultado'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "codigo": {
                    "type": "string",
                    "description": "Código Python. Exemplo: resultado = df.groupby('categoria')['vendas'].sum().to_string()"
                }
            },
            "required": ["codigo"]
        }
    },
    {
        "name": "gerar_grafico",
        "description": "Gera visualizações dos dados. Sempre prefira gerar um gráfico relevante após análises numéricas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["barras", "linha", "histograma", "pizza", "dispersao", "box"],
                    "description": "barras: comparação entre categorias | linha: evolução temporal | histograma: distribuição de valores | pizza: proporções | dispersao: correlação entre duas colunas | box: distribuição e outliers"
                },
                "coluna_x": {
                    "type": "string",
                    "description": "Nome da coluna do eixo X (ou coluna principal para histograma/pizza/box)"
                },
                "coluna_y": {
                    "type": "string",
                    "description": "Nome da coluna do eixo Y (obrigatório para barras, linha e dispersão)"
                },
                "titulo": {
                    "type": "string",
                    "description": "Título do gráfico (opcional)"
                }
            },
            "required": ["tipo", "coluna_x"]
        }
    }
]


def executar_ferramenta(nome: str, inputs: dict) -> str:
    if nome == "carregar_arquivo":
        return carregar_arquivo(inputs["caminho"])
    elif nome == "analisar_dados":
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


def rodar_agente(mensagem_usuario: str, historico: list = None) -> tuple[list, list]:
    """
    Executa o agente com suporte a histórico de conversa.
    Retorna (historico_atualizado, lista_de_artefatos)
    onde artefatos podem ser texto ou imagens base64.
    """
    if historico is None:
        historico = []

    historico.append({"role": "user", "content": mensagem_usuario})
    artefatos = []

    SYSTEM_PROMPT = """Você é um agente especialista em análise de dados. 
Sua missão é ajudar o usuário a entender seus dados de forma clara e visual.

Diretrizes:
- Sempre explore os dados antes de responder perguntas analíticas
- Gere gráficos relevantes sempre que fizer sentido para a análise
- Explique os resultados em linguagem simples, sem jargão desnecessário
- Se os dados tiverem problemas (nulos, inconsistências), aponte proativamente
- Responda em português brasileiro
"""

    while True:
        resposta = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
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

            resultados_ferramentas = []
            for bloco in resposta.content:
                if bloco.type == "tool_use":
                    resultado = executar_ferramenta(bloco.name, bloco.input)

                    # Detecta se é um gráfico em base64
                    if resultado.startswith("GRAFICO_BASE64:"):
                        img_data = resultado.replace("GRAFICO_BASE64:", "")
                        artefatos.append({"tipo": "imagem", "conteudo": img_data, "ferramenta": bloco.name})
                        resultado = "Gráfico gerado com sucesso."

                    resultados_ferramentas.append({
                        "type": "tool_result",
                        "tool_use_id": bloco.id,
                        "content": resultado
                    })

            historico.append({"role": "user", "content": resultados_ferramentas})

    return historico, artefatos
