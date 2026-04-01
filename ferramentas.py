import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

_fallback_df = {}

def _get_df():
    """Retorna o dataframe ativo — do session_state quando no Streamlit, ou do fallback."""
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            return st.session_state.get("df", None)
    except Exception:
        pass
    return _fallback_df.get("df")

def carregar_dataframe(df: pd.DataFrame) -> str:
    """Carrega um DataFrame direto (chamado pelo app.py após upload)."""
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            st.session_state["df"] = df
        else:
            _fallback_df["df"] = df
    except Exception:
        _fallback_df["df"] = df
    return f"linhas={df.shape[0]}, colunas={df.shape[1]}, colunas={list(df.columns)}"

def carregar_arquivo(caminho: str) -> str:
    try:
        if caminho.endswith(".csv"):
            df = pd.read_csv(caminho)
        elif caminho.endswith((".xlsx", ".xls")):
            df = pd.read_excel(caminho)
        else:
            return "Formato não suportado. Use CSV ou Excel."
        carregar_dataframe(df)
        return f"Arquivo carregado: {df.shape[0]} linhas, {df.shape[1]} colunas. Colunas: {list(df.columns)}"
    except Exception as e:
        return f"Erro ao carregar: {str(e)}"

def analisar_dados(operacao: str) -> str:
    df = _get_df()
    if df is None:
        return "Nenhum arquivo carregado ainda."
    try:
        if operacao == "resumo":
            return df.describe(include="all").to_string()
        elif operacao == "nulos":
            nulos = df.isnull().sum()
            resultado = nulos[nulos > 0]
            return resultado.to_string() if len(resultado) > 0 else "Nenhum valor nulo encontrado."
        elif operacao == "tipos":
            return df.dtypes.to_string()
        elif operacao == "primeiras_linhas":
            return df.head(5).to_string()
        else:
            return f"Operação '{operacao}' não reconhecida."
    except Exception as e:
        return f"Erro: {str(e)}"

_BLOCKLIST = [
    "import", "subprocess", "__import__", "__builtins__", "__class__",
    "__mro__", "__subclasses__", "open(", "eval(", "exec(",
    "os.", "sys.", "shutil", "socket", "urllib", "requests",
    "pathlib", "builtins", "globals(", "locals(", "vars(",
    "getattr", "setattr", "delattr", "compile(",
    # bloqueia funções de leitura de arquivo do pandas
    "read_csv", "read_excel", "read_json", "read_html",
    "read_parquet", "read_feather", "read_sql", "read_clipboard",
    "read_table", "read_fwf", "read_pickle", "read_orc",
]

def executar_pandas(codigo: str) -> str:
    df = _get_df()
    if df is None:
        return "Nenhum arquivo carregado ainda."

    codigo_lower = codigo.lower()
    for termo in _BLOCKLIST:
        if termo.lower() in codigo_lower:
            return f"Erro: operação não permitida ('{termo}' bloqueado por segurança)."

    try:
        local_vars = {"df": df, "pd": pd}
        exec(codigo, {"__builtins__": {}}, local_vars)
        resultado = local_vars.get("resultado", "Código executado sem variável 'resultado'.")
        return str(resultado)
    except Exception as e:
        return f"Erro ao executar código: {str(e)}"

def gerar_grafico(tipo: str, coluna_x: str, coluna_y: str = None, titulo: str = "") -> str:
    df = _get_df()
    if df is None:
        return "ERRO: Nenhum arquivo carregado."
    if coluna_x not in df.columns:
        return f"ERRO: Coluna '{coluna_x}' não encontrada. Disponíveis: {list(df.columns)}"
    if coluna_y and coluna_y not in df.columns:
        return f"ERRO: Coluna '{coluna_y}' não encontrada. Disponíveis: {list(df.columns)}"
    try:
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor("#0f1117")
        ax.set_facecolor("#1a1d27")
        cor = "#4f8ef7"
        grade = "#2a2d3a"
        ax.tick_params(colors="#aaaaaa", labelsize=9)
        ax.xaxis.label.set_color("#aaaaaa")
        ax.yaxis.label.set_color("#aaaaaa")
        for spine in ax.spines.values():
            spine.set_edgecolor(grade)

        if tipo == "barras":
            dados = df.groupby(coluna_x)[coluna_y].sum().sort_values(ascending=False).head(15)
            bars = ax.bar(dados.index.astype(str), dados.values, color=cor, alpha=0.85, width=0.6)
            ax.bar_label(bars, fmt="%.0f", color="#aaaaaa", fontsize=8, padding=3)
            ax.set_xlabel(coluna_x); ax.set_ylabel(coluna_y)
            plt.xticks(rotation=30, ha="right")
        elif tipo == "linha":
            dados = df.groupby(coluna_x)[coluna_y].sum()
            xs = range(len(dados))
            ax.plot(xs, dados.values, color=cor, linewidth=2.5, marker="o", markersize=4)
            ax.fill_between(xs, dados.values, alpha=0.1, color=cor)
            ax.set_xticks(xs)
            ax.set_xticklabels(dados.index.astype(str), rotation=30, ha="right")
            ax.set_xlabel(coluna_x); ax.set_ylabel(coluna_y)
        elif tipo == "histograma":
            ax.hist(df[coluna_x].dropna(), bins=25, color=cor, alpha=0.8, edgecolor="#0f1117")
            ax.set_xlabel(coluna_x); ax.set_ylabel("Frequência")
        elif tipo == "pizza":
            dados = df[coluna_x].value_counts().head(8)
            cores = ["#4f8ef7","#f7794f","#4ff7a1","#f7d44f","#c44ff7","#4ff7f7","#f74f7a","#7af74f"]
            wedges, texts, autotexts = ax.pie(dados.values, labels=dados.index.astype(str),
                autopct="%1.1f%%", colors=cores[:len(dados)], pctdistance=0.82, startangle=90)
            for t in texts: t.set_color("#cccccc"); t.set_fontsize(9)
            for at in autotexts: at.set_color("white"); at.set_fontsize(8)
        elif tipo == "dispersao":
            ax.scatter(df[coluna_x], df[coluna_y], color=cor, alpha=0.5, s=20)
            ax.set_xlabel(coluna_x); ax.set_ylabel(coluna_y)
        elif tipo == "box":
            bp = ax.boxplot(df[coluna_x].dropna(), patch_artist=True, vert=True, widths=0.5)
            bp["boxes"][0].set_facecolor(cor); bp["boxes"][0].set_alpha(0.7)
            for item in ["whiskers","caps","medians","fliers"]:
                for el in bp[item]: el.set_color("#aaaaaa")
            ax.set_ylabel(coluna_x)

        ax.grid(True, color=grade, linestyle="--", alpha=0.5, linewidth=0.6)
        ax.set_title(titulo or f"{tipo.capitalize()} — {coluna_x}", color="white", fontsize=13, pad=14)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        buf.seek(0)
        return "GRAFICO_BASE64:" + base64.b64encode(buf.read()).decode("utf-8")
    except Exception as e:
        return f"ERRO ao gerar gráfico: {str(e)}"
