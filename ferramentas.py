import ast
import base64
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

_fallback_df = {}


def _get_df():
    """Retorna o dataframe ativo do Streamlit ou do fallback em memoria."""
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is not None:
            return st.session_state.get("df", None)
    except Exception:
        pass
    return _fallback_df.get("df")


def carregar_dataframe(df: pd.DataFrame) -> str:
    """Carrega um DataFrame direto, chamado pelo app apos upload."""
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
            return "Formato nao suportado. Use CSV ou Excel."
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
        if operacao == "nulos":
            nulos = df.isnull().sum()
            resultado = nulos[nulos > 0]
            return resultado.to_string() if len(resultado) > 0 else "Nenhum valor nulo encontrado."
        if operacao == "tipos":
            return df.dtypes.to_string()
        if operacao == "primeiras_linhas":
            return df.head(5).to_string()
        return f"Operacao '{operacao}' nao reconhecida."
    except Exception as e:
        return f"Erro: {str(e)}"


_NOMES_BLOQUEADOS = {
    "__builtins__",
    "__import__",
    "eval",
    "exec",
    "open",
    "compile",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "input",
    "help",
    "dir",
    "type",
    "super",
}

_CHAMADAS_PANDAS_BLOQUEADAS = {
    "read_csv",
    "read_excel",
    "read_json",
    "read_html",
    "read_parquet",
    "read_feather",
    "read_sql",
    "read_clipboard",
    "read_table",
    "read_fwf",
    "read_pickle",
    "read_orc",
    "to_pickle",
    "to_sql",
}

_NOS_AST_BLOQUEADOS = (
    ast.Import,
    ast.ImportFrom,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    ast.Global,
    ast.Nonlocal,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.Raise,
    ast.Delete,
)


def _validar_codigo_pandas(codigo: str) -> str | None:
    try:
        arvore = ast.parse(codigo, mode="exec")
    except SyntaxError as e:
        return f"Erro de sintaxe: {e.msg}"

    for no in ast.walk(arvore):
        if isinstance(no, _NOS_AST_BLOQUEADOS):
            return f"Erro: construcao Python nao permitida ({type(no).__name__})."
        if isinstance(no, ast.Name) and no.id in _NOMES_BLOQUEADOS:
            return f"Erro: nome nao permitido ('{no.id}')."
        if isinstance(no, ast.Attribute):
            if no.attr.startswith("_"):
                return f"Erro: atributo interno nao permitido ('{no.attr}')."
            if no.attr in _CHAMADAS_PANDAS_BLOQUEADAS:
                return f"Erro: operacao nao permitida ('{no.attr}')."
        if isinstance(no, ast.Call):
            func = no.func
            if isinstance(func, ast.Name) and func.id in _NOMES_BLOQUEADOS:
                return f"Erro: chamada nao permitida ('{func.id}')."
            if isinstance(func, ast.Attribute) and func.attr in _CHAMADAS_PANDAS_BLOQUEADAS:
                return f"Erro: operacao nao permitida ('{func.attr}')."

    atribui_resultado = any(
        isinstance(no, ast.Assign)
        and any(isinstance(alvo, ast.Name) and alvo.id == "resultado" for alvo in no.targets)
        for no in ast.walk(arvore)
    )
    if not atribui_resultado:
        return "Erro: defina a variavel 'resultado' com o valor final da analise."

    return None


def executar_pandas(codigo: str) -> str:
    df = _get_df()
    if df is None:
        return "Nenhum arquivo carregado ainda."

    erro_validacao = _validar_codigo_pandas(codigo)
    if erro_validacao:
        return erro_validacao

    try:
        local_vars = {"df": df.copy(), "pd": pd}
        exec(codigo, {"__builtins__": {}}, local_vars)
        resultado = local_vars.get("resultado", "Codigo executado sem variavel 'resultado'.")
        return str(resultado)
    except Exception as e:
        return f"Erro ao executar codigo: {str(e)}"


def gerar_grafico(tipo: str, coluna_x: str, coluna_y: str = None, titulo: str = "") -> str:
    df = _get_df()
    if df is None:
        return "ERRO: Nenhum arquivo carregado."
    if coluna_x not in df.columns:
        return f"ERRO: Coluna '{coluna_x}' nao encontrada. Disponiveis: {list(df.columns)}"
    if coluna_y and coluna_y not in df.columns:
        return f"ERRO: Coluna '{coluna_y}' nao encontrada. Disponiveis: {list(df.columns)}"

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
            if coluna_y:
                dados = df.groupby(coluna_x)[coluna_y].sum().sort_values(ascending=False).head(15)
                ylabel = coluna_y
            else:
                dados = df[coluna_x].value_counts().head(15)
                ylabel = "Frequencia"
            bars = ax.bar(dados.index.astype(str), dados.values, color=cor, alpha=0.85, width=0.6)
            ax.bar_label(bars, fmt="%.0f", color="#aaaaaa", fontsize=8, padding=3)
            ax.set_xlabel(coluna_x)
            ax.set_ylabel(ylabel)
            plt.xticks(rotation=30, ha="right")
        elif tipo == "linha":
            if not coluna_y:
                return "ERRO: coluna_y e obrigatoria para grafico de linha."
            dados = df.groupby(coluna_x)[coluna_y].sum()
            xs = range(len(dados))
            ax.plot(xs, dados.values, color=cor, linewidth=2.5, marker="o", markersize=4)
            ax.fill_between(xs, dados.values, alpha=0.1, color=cor)
            ax.set_xticks(xs)
            ax.set_xticklabels(dados.index.astype(str), rotation=30, ha="right")
            ax.set_xlabel(coluna_x)
            ax.set_ylabel(coluna_y)
        elif tipo == "histograma":
            ax.hist(df[coluna_x].dropna(), bins=25, color=cor, alpha=0.8, edgecolor="#0f1117")
            ax.set_xlabel(coluna_x)
            ax.set_ylabel("Frequencia")
        elif tipo == "pizza":
            dados = df[coluna_x].value_counts().head(8)
            cores = ["#4f8ef7", "#f7794f", "#4ff7a1", "#f7d44f", "#c44ff7", "#4ff7f7", "#f74f7a", "#7af74f"]
            wedges, texts, autotexts = ax.pie(
                dados.values,
                labels=dados.index.astype(str),
                autopct="%1.1f%%",
                colors=cores[: len(dados)],
                pctdistance=0.82,
                startangle=90,
            )
            for text in texts:
                text.set_color("#cccccc")
                text.set_fontsize(9)
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_fontsize(8)
        elif tipo == "dispersao":
            if not coluna_y:
                return "ERRO: coluna_y e obrigatoria para grafico de dispersao."
            ax.scatter(df[coluna_x], df[coluna_y], color=cor, alpha=0.5, s=20)
            ax.set_xlabel(coluna_x)
            ax.set_ylabel(coluna_y)
        elif tipo == "box":
            bp = ax.boxplot(df[coluna_x].dropna(), patch_artist=True, vert=True, widths=0.5)
            bp["boxes"][0].set_facecolor(cor)
            bp["boxes"][0].set_alpha(0.7)
            for item in ["whiskers", "caps", "medians", "fliers"]:
                for el in bp[item]:
                    el.set_color("#aaaaaa")
            ax.set_ylabel(coluna_x)
        else:
            return f"ERRO: Tipo de grafico '{tipo}' nao reconhecido."

        ax.grid(True, color=grade, linestyle="--", alpha=0.5, linewidth=0.6)
        ax.set_title(titulo or f"{tipo.capitalize()} - {coluna_x}", color="white", fontsize=13, pad=14)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        buf.seek(0)
        return "GRAFICO_BASE64:" + base64.b64encode(buf.read()).decode("utf-8")
    except Exception as e:
        return f"ERRO ao gerar grafico: {str(e)}"
