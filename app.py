import streamlit as st
import pandas as pd
import base64
import io
from ferramentas import carregar_dataframe, analisar_dados
from agente import rodar_agente

# ─── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agente de Dados",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS customizado ───────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Fundo geral */
.stApp {
    background-color: #0c0e1a;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0f1120;
    border-right: 1px solid #1e2235;
}

section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: #e2e8f0;
}

/* Título principal */
.titulo-app {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
    line-height: 1.2;
}

.titulo-sub {
    font-size: 0.85rem;
    color: #5a6380;
    font-weight: 400;
    margin-top: 2px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* Cards de métrica */
.metric-card {
    background: #131626;
    border: 1px solid #1e2235;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 8px;
}

.metric-label {
    font-size: 0.72rem;
    color: #5a6380;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}

.metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #4f8ef7;
}

.metric-sub {
    font-size: 0.75rem;
    color: #8892a4;
    margin-top: 2px;
}

/* Área do chat */
.chat-container {
    background: #0f1120;
    border-radius: 12px;
    border: 1px solid #1e2235;
    padding: 8px 0;
    min-height: 400px;
}

.msg-user {
    background: #1a1f35;
    border-radius: 10px 10px 2px 10px;
    padding: 10px 14px;
    margin: 6px 20px 6px 60px;
    color: #e2e8f0;
    font-size: 0.9rem;
    line-height: 1.5;
}

.msg-agent {
    background: #131626;
    border-radius: 10px 10px 10px 2px;
    padding: 10px 14px;
    margin: 6px 60px 6px 20px;
    color: #c8d0e0;
    font-size: 0.9rem;
    line-height: 1.6;
    border-left: 2px solid #4f8ef7;
}

.tag-user {
    font-size: 0.68rem;
    color: #5a6380;
    margin: 10px 20px 2px 60px;
    text-align: right;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

.tag-agent {
    font-size: 0.68rem;
    color: #4f8ef7;
    margin: 10px 60px 2px 20px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* Upload area */
.upload-area {
    border: 1.5px dashed #2a3050;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    background: #131626;
    transition: border-color 0.2s;
}

/* Chip de status */
.status-chip {
    display: inline-block;
    background: #0f2d1f;
    border: 1px solid #1a5c38;
    color: #4ade80;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.72rem;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.5px;
}

.status-chip-warn {
    background: #2d1f0f;
    border: 1px solid #5c3a1a;
    color: #fb923c;
}

/* Divider */
.divider {
    height: 1px;
    background: linear-gradient(to right, transparent, #1e2235, transparent);
    margin: 12px 0;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0c0e1a; }
::-webkit-scrollbar-thumb { background: #2a3050; border-radius: 2px; }

/* Input do chat */
.stTextInput input {
    background-color: #131626 !important;
    border: 1px solid #1e2235 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
}

.stTextInput input:focus {
    border-color: #4f8ef7 !important;
    box-shadow: 0 0 0 2px rgba(79, 142, 247, 0.15) !important;
}

/* Botão */
.stButton button {
    background: #4f8ef7;
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 8px 20px;
    transition: background 0.2s;
}

.stButton button:hover {
    background: #3a7ae6;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: #131626;
    border: 1.5px dashed #2a3050;
    border-radius: 10px;
    padding: 10px;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #1e2235;
    border-radius: 8px;
    overflow: hidden;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #0f1120;
    border-bottom: 1px solid #1e2235;
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    color: #5a6380;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    font-weight: 500;
    padding: 8px 16px;
    border-radius: 6px 6px 0 0;
}

.stTabs [aria-selected="true"] {
    color: #4f8ef7 !important;
    background: #131626 !important;
    border-bottom: 2px solid #4f8ef7 !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Estado da sessão ──────────────────────────────────────────────────────────
if "historico_agente" not in st.session_state:
    st.session_state.historico_agente = []

if "mensagens_ui" not in st.session_state:
    st.session_state.mensagens_ui = []

if "df" not in st.session_state:
    st.session_state.df = None

if "arquivo_nome" not in st.session_state:
    st.session_state.arquivo_nome = None



# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="titulo-app">◈ Agente<br>de Dados</div>', unsafe_allow_html=True)
    st.markdown('<div class="titulo-sub">Análise inteligente com IA</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Upload de arquivo
    st.markdown("**Carregar dados**")
    arquivo = st.file_uploader(
        "Solte aqui seu CSV ou Excel",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed"
    )

    if arquivo and arquivo.name != st.session_state.arquivo_nome:
        with st.spinner("Carregando..."):
            try:
                if arquivo.name.endswith(".csv"):
                    df = pd.read_csv(arquivo)
                else:
                    df = pd.read_excel(arquivo)

                st.session_state.df = df
                st.session_state.arquivo_nome = arquivo.name
                carregar_dataframe(df)

                st.session_state.mensagens_ui.append({
                    "role": "agent",
                    "tipo": "texto",
                    "conteudo": f"Arquivo **{arquivo.name}** carregado com sucesso.\n\n**{df.shape[0]:,}** linhas · **{df.shape[1]}** colunas\n\nColunas: `{'`, `'.join(df.columns.tolist())}`\n\nComo posso te ajudar a analisar esses dados?"
                })
                st.session_state.historico_agente = []

            except Exception as e:
                st.error(f"Erro: {str(e)}")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Status do arquivo
    if st.session_state.df is not None:
        df = st.session_state.df
        nulos = df.isnull().sum().sum()

        st.markdown(f'<span class="status-chip">● {st.session_state.arquivo_nome}</span>', unsafe_allow_html=True)
        st.markdown("")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Linhas</div>
                <div class="metric-value">{df.shape[0]:,}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Colunas</div>
                <div class="metric-value">{df.shape[1]}</div>
            </div>""", unsafe_allow_html=True)

        if nulos > 0:
            st.markdown(f'<span class="status-chip status-chip-warn">⚠ {nulos} valores nulos</span>', unsafe_allow_html=True)
            st.markdown("")

    else:
        st.markdown('<span class="status-chip status-chip-warn">○ Nenhum arquivo</span>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Sugestões rápidas
    st.markdown("**Perguntas sugeridas**")
    sugestoes = [
        "Faça uma análise geral dos dados",
        "Quais colunas têm valores nulos?",
        "Mostre a distribuição da primeira coluna numérica",
        "Quais são os top 10 valores mais frequentes?",
    ]
    for s in sugestoes:
        if st.button(s, key=f"sug_{s}", use_container_width=True):
            st.session_state._sugestao = s

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    if st.button("🗑 Limpar conversa", use_container_width=True):
        st.session_state.mensagens_ui = []
        st.session_state.historico_agente = []
        st.rerun()


# ─── Área principal ────────────────────────────────────────────────────────────
col_chat, col_dados = st.columns([3, 2], gap="medium")

with col_chat:
    st.markdown("### Conversa")

    # Exibe mensagens
    chat_area = st.container()
    with chat_area:
        if not st.session_state.mensagens_ui:
            st.markdown("""
            <div style="text-align:center; padding: 60px 20px; color: #3a4060;">
                <div style="font-size: 2rem; margin-bottom: 12px;">◈</div>
                <div style="font-family: 'Space Mono', monospace; font-size: 0.85rem;">
                    Carregue um arquivo para começar
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.mensagens_ui:
                if msg["role"] == "user":
                    st.markdown(f'<div class="tag-user">você</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="msg-user">{msg["conteudo"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="tag-agent">◈ agente</div>', unsafe_allow_html=True)
                    if msg["tipo"] == "imagem":
                        img_bytes = base64.b64decode(msg["conteudo"])
                        st.image(img_bytes, use_container_width=True)
                    else:
                        st.markdown(f'<div class="msg-agent">{msg["conteudo"]}</div>', unsafe_allow_html=True)

    st.markdown("")

    # Input do chat — st.form garante que o agente só roda no submit explícito
    # (botão Enviar ou Enter dentro do campo), nunca ao perder o foco.
    # clear_on_submit=True limpa o campo automaticamente após o envio.
    with st.form(key="chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            entrada = st.text_input(
                "Mensagem",
                placeholder="Pergunte algo sobre os dados...",
                label_visibility="collapsed",
                value=getattr(st.session_state, "_sugestao", "")
            )
            if hasattr(st.session_state, "_sugestao"):
                del st.session_state._sugestao
        with col_btn:
            enviar = st.form_submit_button("Enviar", use_container_width=True)

    if enviar and entrada.strip():
        if st.session_state.df is None:
            st.warning("Carregue um arquivo antes de fazer perguntas.")
        else:
            st.session_state.mensagens_ui.append({
                "role": "user",
                "tipo": "texto",
                "conteudo": entrada.strip()
            })
            with st.spinner("Analisando..."):
                historico_atualizado, artefatos = rodar_agente(
                    entrada.strip(),
                    st.session_state.historico_agente
                )
                st.session_state.historico_agente = historico_atualizado
                for artefato in artefatos:
                    st.session_state.mensagens_ui.append({
                        "role": "agent",
                        "tipo": artefato["tipo"],
                        "conteudo": artefato["conteudo"]
                    })
            st.rerun()


# ─── Painel de dados ───────────────────────────────────────────────────────────
with col_dados:
    st.markdown("### Dados")

    if st.session_state.df is not None:
        df = st.session_state.df

        tab1, tab2, tab3 = st.tabs(["Preview", "Estatísticas", "Colunas"])

        with tab1:
            st.dataframe(df.head(50), use_container_width=True, height=400)

        with tab2:
            try:
                desc = df.describe(include="all").round(2)
                st.dataframe(desc, use_container_width=True, height=400)
            except:
                st.info("Não foi possível gerar estatísticas.")

        with tab3:
            col_info = pd.DataFrame({
                "Coluna": df.columns,
                "Tipo": df.dtypes.astype(str).values,
                "Nulos": df.isnull().sum().values,
                "Únicos": df.nunique().values,
            })
            st.dataframe(col_info, use_container_width=True, hide_index=True, height=400)

    else:
        st.markdown("""
        <div style="text-align:center; padding: 80px 20px; color: #3a4060;">
            <div style="font-size: 2.5rem; margin-bottom: 12px;">⬆</div>
            <div style="font-size: 0.85rem; font-family: 'Space Mono', monospace;">
                Carregue um arquivo<br>na barra lateral
            </div>
        </div>
        """, unsafe_allow_html=True)
