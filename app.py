import base64
import html

import pandas as pd
import streamlit as st

from agente import rodar_agente
from ferramentas import carregar_dataframe


st.set_page_config(
    page_title="Agente de Dados",
    page_icon="DA",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
html, body, [class*="css"] { font-family: Arial, sans-serif; }
.stApp { background-color: #0c0e1a; color: #e2e8f0; }
section[data-testid="stSidebar"] {
    background-color: #0f1120;
    border-right: 1px solid #1e2235;
}
.titulo-app {
    font-size: 1.55rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
}
.titulo-sub {
    font-size: 0.8rem;
    color: #8a93aa;
    margin-top: 4px;
    text-transform: uppercase;
}
.metric-card {
    background: #131626;
    border: 1px solid #1e2235;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
.metric-label {
    font-size: 0.72rem;
    color: #8a93aa;
    text-transform: uppercase;
}
.metric-value {
    font-size: 1.45rem;
    font-weight: 800;
    color: #4f8ef7;
}
.msg-user, .msg-agent {
    border-radius: 8px;
    padding: 10px 14px;
    color: #e2e8f0;
    font-size: 0.92rem;
    line-height: 1.55;
    overflow-wrap: anywhere;
}
.msg-user {
    background: #1a1f35;
    margin: 6px 20px 6px 60px;
}
.msg-agent {
    background: #131626;
    border-left: 2px solid #4f8ef7;
    margin: 6px 60px 6px 20px;
}
.tag-user, .tag-agent {
    font-size: 0.68rem;
    color: #8a93aa;
    margin-top: 10px;
    text-transform: uppercase;
}
.tag-user { margin-right: 20px; text-align: right; }
.tag-agent { margin-left: 20px; color: #4f8ef7; }
.status-chip {
    display: inline-block;
    background: #0f2d1f;
    border: 1px solid #1a5c38;
    color: #4ade80;
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 0.76rem;
}
.status-chip-warn {
    background: #2d1f0f;
    border-color: #5c3a1a;
    color: #fb923c;
}
.divider {
    height: 1px;
    background: linear-gradient(to right, transparent, #1e2235, transparent);
    margin: 14px 0;
}
.stTextInput input {
    background-color: #131626 !important;
    border: 1px solid #1e2235 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
.stButton button {
    background: #4f8ef7;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 700;
}
[data-testid="stFileUploader"] {
    background: #131626;
    border: 1px dashed #2a3050;
    border-radius: 8px;
    padding: 10px;
}
</style>
""",
    unsafe_allow_html=True,
)


def _safe_html(texto: str) -> str:
    return html.escape(str(texto)).replace("\n", "<br>")


def _add_agent_text(texto: str) -> None:
    st.session_state.mensagens_ui.append({"role": "agent", "tipo": "texto", "conteudo": texto})


for chave, valor in {
    "historico_agente": [],
    "mensagens_ui": [],
    "df": None,
    "arquivo_nome": None,
}.items():
    if chave not in st.session_state:
        st.session_state[chave] = valor


with st.sidebar:
    st.markdown('<div class="titulo-app">Data Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="titulo-sub">Analise inteligente com OpenAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown("**Carregar dados**")
    arquivo = st.file_uploader(
        "Solte aqui seu CSV ou Excel",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed",
    )

    if arquivo and arquivo.name != st.session_state.arquivo_nome:
        with st.spinner("Carregando..."):
            try:
                if arquivo.name.lower().endswith(".csv"):
                    df = pd.read_csv(arquivo)
                else:
                    df = pd.read_excel(arquivo)

                st.session_state.df = df
                st.session_state.arquivo_nome = arquivo.name
                carregar_dataframe(df)
                st.session_state.historico_agente = []
                st.session_state.mensagens_ui = []
                _add_agent_text(
                    f"Arquivo {arquivo.name} carregado com sucesso.\n\n"
                    f"{df.shape[0]:,} linhas, {df.shape[1]} colunas.\n\n"
                    f"Colunas: {', '.join(map(str, df.columns.tolist()))}\n\n"
                    "Como posso ajudar a analisar esses dados?"
                )
            except Exception as e:
                st.error(f"Erro ao carregar arquivo: {str(e)}")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    if st.session_state.df is not None:
        df = st.session_state.df
        nulos = int(df.isnull().sum().sum())
        nome_arquivo = _safe_html(st.session_state.arquivo_nome)
        st.markdown(f'<span class="status-chip">{nome_arquivo}</span>', unsafe_allow_html=True)
        st.markdown("")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Linhas</div>'
                f'<div class="metric-value">{df.shape[0]:,}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Colunas</div>'
                f'<div class="metric-value">{df.shape[1]}</div></div>',
                unsafe_allow_html=True,
            )
        if nulos:
            st.markdown(f'<span class="status-chip status-chip-warn">{nulos} valores nulos</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-chip status-chip-warn">Nenhum arquivo</span>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("**Perguntas sugeridas**")
    sugestoes = [
        "Faca uma analise geral dos dados",
        "Quais colunas tem valores nulos?",
        "Mostre a distribuicao da primeira coluna numerica",
        "Quais sao os top 10 valores mais frequentes?",
    ]
    for sugestao in sugestoes:
        if st.button(sugestao, key=f"sug_{sugestao}", use_container_width=True):
            st.session_state._sugestao = sugestao

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    if st.button("Limpar conversa", use_container_width=True):
        st.session_state.mensagens_ui = []
        st.session_state.historico_agente = []
        st.rerun()


col_chat, col_dados = st.columns([3, 2], gap="medium")

with col_chat:
    st.markdown("### Conversa")

    if not st.session_state.mensagens_ui:
        st.info("Carregue um arquivo para comecar.")
    else:
        for msg in st.session_state.mensagens_ui:
            if msg["role"] == "user":
                st.markdown('<div class="tag-user">voce</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="msg-user">{_safe_html(msg["conteudo"])}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="tag-agent">agente</div>', unsafe_allow_html=True)
                if msg["tipo"] == "imagem":
                    img_bytes = base64.b64decode(msg["conteudo"])
                    st.image(img_bytes, use_container_width=True)
                else:
                    st.markdown(f'<div class="msg-agent">{_safe_html(msg["conteudo"])}</div>', unsafe_allow_html=True)

    with st.form(key="chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            entrada = st.text_input(
                "Mensagem",
                placeholder="Pergunte algo sobre os dados...",
                label_visibility="collapsed",
                value=getattr(st.session_state, "_sugestao", ""),
            )
            if hasattr(st.session_state, "_sugestao"):
                del st.session_state._sugestao
        with col_btn:
            enviar = st.form_submit_button("Enviar", use_container_width=True)

    if enviar and entrada.strip():
        if st.session_state.df is None:
            st.warning("Carregue um arquivo antes de fazer perguntas.")
        else:
            st.session_state.mensagens_ui.append({"role": "user", "tipo": "texto", "conteudo": entrada.strip()})
            with st.spinner("Analisando..."):
                historico_atualizado, artefatos = rodar_agente(entrada.strip(), st.session_state.historico_agente)
                st.session_state.historico_agente = historico_atualizado
                for artefato in artefatos:
                    st.session_state.mensagens_ui.append(
                        {"role": "agent", "tipo": artefato["tipo"], "conteudo": artefato["conteudo"]}
                    )
            st.rerun()


with col_dados:
    st.markdown("### Dados")

    if st.session_state.df is None:
        st.info("Carregue um arquivo na barra lateral.")
    else:
        df = st.session_state.df
        tab1, tab2, tab3 = st.tabs(["Preview", "Estatisticas", "Colunas"])

        with tab1:
            st.dataframe(df.head(50), use_container_width=True, height=400)

        with tab2:
            try:
                desc = df.describe(include="all").round(2)
                st.dataframe(desc, use_container_width=True, height=400)
            except Exception:
                st.info("Nao foi possivel gerar estatisticas.")

        with tab3:
            col_info = pd.DataFrame(
                {
                    "Coluna": df.columns,
                    "Tipo": df.dtypes.astype(str).values,
                    "Nulos": df.isnull().sum().values,
                    "Unicos": df.nunique().values,
                }
            )
            st.dataframe(col_info, use_container_width=True, hide_index=True, height=400)
