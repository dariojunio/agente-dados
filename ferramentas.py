import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os
import io
import base64

df_global = None  # guarda o dataframe em memória


def carregar_arquivo(caminho: str) -> str:
    global df_global
    try:
        if caminho.endswith(".csv"):
            df_global = pd.read_csv(caminho)
        elif caminho.endswith((".xlsx", ".xls")):
            df_global = pd.read_excel(caminho)
        else:
            return "Formato não suportado. Use CSV ou Excel."

        info = {
            "linhas": df_global.shape[0],
            "colunas": df_global.shape[1],
            "nomes_colunas": list(df_global.columns),
            "tipos": df_global.dtypes.astype(str).to_dict(),
            "preview": df_global.head(3).to_dict(orient="records"),
        }
        return str(info)
    except Exception as e:
        return f"Erro ao carregar: {str(e)}"


def carregar_dataframe(df: pd.DataFrame) -> str:
    """Carrega um DataFrame diretamente (usado pelo Streamlit via upload)."""
    global df_global
    df_global = df
    info = {
        "linhas": df_global.shape[0],
        "colunas": df_global.shape[1],
        "nomes_colunas": list(df_global.columns),
        "tipos": df_global.dtypes.astype(str).to_dict(),
        "preview": df_global.head(3).to_dict(orient="records"),
    }
    return str(info)


def get_dataframe():
    return df_global


def analisar_dados(operacao: str) -> str:
    global df_global
    if df_global is None:
        return "Nenhum arquivo carregado ainda."

    try:
        if operacao == "resumo":
            return df_global.describe(include="all").to_string()
        elif operacao == "nulos":
            nulos = df_global.isnull().sum()
            resultado = nulos[nulos > 0]
            return resultado.to_string() if len(resultado) > 0 else "Nenhum valor nulo encontrado."
        elif operacao == "tipos":
            return df_global.dtypes.to_string()
        elif operacao == "primeiras_linhas":
            return df_global.head(5).to_string()
        else:
            return f"Operação '{operacao}' não reconhecida."
    except Exception as e:
        return f"Erro na análise: {str(e)}"


def executar_pandas(codigo: str) -> str:
    global df_global
    if df_global is None:
        return "Nenhum arquivo carregado ainda."

    try:
        local_vars = {"df": df_global, "pd": pd}
        exec(codigo, {}, local_vars)
        resultado = local_vars.get("resultado", "Código executado, mas nenhuma variável 'resultado' foi definida.")
        return str(resultado)
    except Exception as e:
        return f"Erro ao executar código: {str(e)}"


def gerar_grafico(tipo: str, coluna_x: str, coluna_y: str = None, titulo: str = "") -> str:
    """
    Gera um gráfico e retorna a imagem em base64 para exibir no Streamlit.
    Formatos suportados: barras, linha, histograma, pizza, dispersao, box
    """
    global df_global
    if df_global is None:
        return "ERRO: Nenhum arquivo carregado ainda."

    if coluna_x not in df_global.columns:
        return f"ERRO: Coluna '{coluna_x}' não encontrada. Colunas disponíveis: {list(df_global.columns)}"

    if coluna_y and coluna_y not in df_global.columns:
        return f"ERRO: Coluna '{coluna_y}' não encontrada. Colunas disponíveis: {list(df_global.columns)}"

    try:
        # Estilo do gráfico
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("#0f1117")
        ax.set_facecolor("#1a1d27")

        cor_principal = "#4f8ef7"
        cor_grade = "#2a2d3a"

        ax.tick_params(colors="#aaaaaa", labelsize=9)
        ax.xaxis.label.set_color("#aaaaaa")
        ax.yaxis.label.set_color("#aaaaaa")
        for spine in ax.spines.values():
            spine.set_edgecolor(cor_grade)

        if tipo == "barras":
            dados = df_global.groupby(coluna_x)[coluna_y].sum().sort_values(ascending=False).head(15)
            bars = ax.bar(dados.index.astype(str), dados.values, color=cor_principal, alpha=0.85, width=0.6)
            ax.bar_label(bars, fmt="%.0f", color="#aaaaaa", fontsize=8, padding=3)
            ax.set_xlabel(coluna_x)
            ax.set_ylabel(coluna_y)
            plt.xticks(rotation=30, ha="right")

        elif tipo == "linha":
            dados = df_global.groupby(coluna_x)[coluna_y].sum()
            ax.plot(dados.index.astype(str), dados.values, color=cor_principal, linewidth=2.5, marker="o", markersize=4)
            ax.fill_between(range(len(dados)), dados.values, alpha=0.1, color=cor_principal)
            ax.set_xlabel(coluna_x)
            ax.set_ylabel(coluna_y)
            plt.xticks(rotation=30, ha="right")
            ax.set_xticks(range(len(dados)))
            ax.set_xticklabels(dados.index.astype(str), rotation=30, ha="right")

        elif tipo == "histograma":
            ax.hist(df_global[coluna_x].dropna(), bins=25, color=cor_principal, alpha=0.8, edgecolor="#0f1117")
            ax.set_xlabel(coluna_x)
            ax.set_ylabel("Frequência")

        elif tipo == "pizza":
            dados = df_global[coluna_x].value_counts().head(8)
            cores = ["#4f8ef7", "#f7794f", "#4ff7a1", "#f7d44f", "#c44ff7", "#4ff7f7", "#f74f7a", "#7af74f"]
            wedges, texts, autotexts = ax.pie(
                dados.values, labels=dados.index.astype(str),
                autopct="%1.1f%%", colors=cores[:len(dados)],
                pctdistance=0.82, startangle=90
            )
            for t in texts:
                t.set_color("#cccccc")
                t.set_fontsize(9)
            for at in autotexts:
                at.set_color("white")
                at.set_fontsize(8)

        elif tipo == "dispersao":
            ax.scatter(df_global[coluna_x], df_global[coluna_y], color=cor_principal, alpha=0.5, s=20)
            ax.set_xlabel(coluna_x)
            ax.set_ylabel(coluna_y)

        elif tipo == "box":
            dados_box = df_global[coluna_x].dropna()
            bp = ax.boxplot(dados_box, patch_artist=True, vert=True, widths=0.5)
            bp["boxes"][0].set_facecolor(cor_principal)
            bp["boxes"][0].set_alpha(0.7)
            for item in ["whiskers", "caps", "medians", "fliers"]:
                for el in bp[item]:
                    el.set_color("#aaaaaa")
            ax.set_ylabel(coluna_x)

        ax.grid(True, color=cor_grade, linestyle="--", alpha=0.5, linewidth=0.6)
        ax.set_title(titulo or f"{tipo.capitalize()} — {coluna_x}", color="white", fontsize=13, pad=14)

        plt.tight_layout()

        # Retorna como base64 para exibir no Streamlit
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"GRAFICO_BASE64:{img_base64}"

    except Exception as e:
        return f"ERRO ao gerar gráfico: {str(e)}"
