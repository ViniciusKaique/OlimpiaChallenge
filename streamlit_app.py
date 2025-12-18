import streamlit as st
import yfinance as yf
import pandas as pd

# ==============================================================================
# 1. MAPEAMENTO DE LOGOS (A SOLUÇÃO DEFINITIVA)
# ==============================================================================
# O Yahoo Finance falha muito nos logos. A melhor solução gratuita é mapear
# o Ticker -> Site da Empresa e usar a API da Clearbit.
# ==============================================================================
EMPRESAS_DOMINIOS = {
    "VALE3": "vale.com", "PETR4": "petrobras.com.br", "ITUB4": "itau.com.br",
    "BBDC4": "bradesco.com.br", "BBAS3": "bb.com.br", "WEGE3": "weg.net",
    "ABEV3": "ambev.com.br", "RENT3": "localiza.com", "BPAC11": "btgpactual.com",
    "SUZB3": "suzano.com.br", "HAPV3": "hapvida.com.br", "RDOR3": "rededorsaoluiz.com.br",
    "B3SA3": "b3.com.br", "EQTL3": "equatorialenergia.com.br", "PRIO3": "prio3.com.br",
    "RAIL3": "rumolog.com", "GGBR4": "gerdau.com.br", "JBSS3": "jbs.com.br",
    "VIVT3": "telefonica.com.br", "CSAN3": "cosan.com.br", "ELET3": "eletrobras.com",
    "MGLU3": "magazineluiza.com.br", "LREN3": "lojasrenner.com.br", "AZUL4": "voeazul.com.br",
    "GOLL4": "voegol.com.br", "HYPE3": "hypera.com.br", "CMIG4": "cemig.com.br"
}

LISTA_ACOES = [f"{t}.SA" for t in EMPRESAS_DOMINIOS.keys()]

# ==============================================================================
# 2. CONFIGURAÇÃO VISUAL (CSS)
# ==============================================================================
st.set_page_config(layout="wide", page_title="Step 1: Logos e Layout")

st.markdown("""
<style>
    /* Ajusta padding para caber tudo na tela */
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    
    /* Card da Ação */
    .stock-card {
        background-color: #262730;
        border: 1px solid #3f3f46;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    /* Imagem do Logo */
    .logo-img {
        width: 35px; height: 35px;
        border-radius: 50%;
        object-fit: contain; /* Garante que o logo não distorça */
        background-color: #fff; /* Fundo branco para logos transparentes */
        padding: 2px;
        margin-right: 10px;
    }
    
    .ticker-name { font-weight: bold; font-size: 1rem; color: #fff; }
    .ticker-price { font-size: 0.85rem; color: #a1a1aa; }
    
    .badge {
        padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9rem;
    }
    .badge-up { background-color: rgba(74, 222, 128, 0.2); color: #4ade80; }
    .badge-down { background-color: rgba(248, 113, 113, 0.2); color: #f87171; }
    
    /* Input do Langchain fixo embaixo */
    .stTextInput input {
        border-radius: 20px;
        border: 1px solid #3f3f46;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. LÓGICA DE DADOS
# ==============================================================================
@st.cache_data(ttl=300)
def get_data_simple():
    # Baixa dados de 2 dias para calcular variação
    df = yf.download(LISTA_ACOES, period="2d", progress=False)['Close']
    
    # Calcula variação percentual
    var_pct = ((df.iloc[-1] - df.iloc[-2]) / df.iloc[-2]) * 100
    preco_atual = df.iloc[-1]
    
    res = pd.DataFrame({'Var': var_pct, 'Preco': preco_atual})
    res.index = res.index.str.replace('.SA', '') # Remove .SA do nome para o logo funcionar
    
    top_altas = res.sort_values('Var', ascending=False).head(5)
    top_baixas = res.sort_values('Var', ascending=True).head(5)
    
    return top_altas, top_baixas

# ==============================================================================
# 4. RENDERIZAÇÃO DA PÁGINA
# ==============================================================================

# Busca Dados
altas, baixas = get_data_simple()

# Título
st.subheader("📊 Monitoramento de Mercado")

# --- LAYOUT PRINCIPAL: 2 COLUNAS ---
col_esq, col_dir = st.columns(2, gap="large")

# Função para criar o HTML do Card
def render_card(ticker, row, tipo):
    # Lógica do Logo: Pega o domínio do dicionário, se não tiver, usa google
    domain = EMPRESAS_DOMINIOS.get(ticker, 'google.com')
    logo_url = f"https://logo.clearbit.com/{domain}"
    
    # Classe de cor (verde ou vermelho)
    css_class = "badge-up" if tipo == "alta" else "badge-down"
    sinal = "+" if tipo == "alta" else ""
    
    return f"""
    <div class="stock-card">
        <div style="display:flex; align-items:center;">
            <img src="{logo_url}" class="logo-img" onerror="this.src='https://via.placeholder.com/35'">
            <div>
                <div class="ticker-name">{ticker}</div>
                <div class="ticker-price">R$ {row['Preco']:.2f}</div>
            </div>
        </div>
        <div class="badge {css_class}">
            {sinal}{row['Var']:.2f}%
        </div>
    </div>
    """

# Coluna 1: ALTAS
with col_esq:
    st.markdown("##### 🚀 Maiores Altas")
    for ticker, row in altas.iterrows():
        st.markdown(render_card(ticker, row, "alta"), unsafe_allow_html=True)

# Coluna 2: BAIXAS
with col_dir:
    st.markdown("##### 🔻 Maiores Baixas")
    for ticker, row in baixas.iterrows():
        st.markdown(render_card(ticker, row, "baixa"), unsafe_allow_html=True)

st.divider()

# --- ÁREA DO LANGCHAIN (EMBAIXO) ---
# Aqui entrará a lógica da IA depois. Por enquanto é só o visual.
st.markdown("##### 🤖 Assistente Financeiro (LangChain)")
pergunta = st.text_input("", placeholder="Ex: Analise a performance da Vale hoje...")

if pergunta:
    st.info(f"Você digitou: '{pergunta}'. Na próxima etapa ligaremos isso ao Gemini.")