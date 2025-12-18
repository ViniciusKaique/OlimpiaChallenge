import streamlit as st
import yfinance as yf
import pandas as pd

# ==============================================================================
# 1. DADOS E DOMÍNIOS
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
# 2. CONFIGURAÇÃO VISUAL
# ==============================================================================
st.set_page_config(layout="wide", page_title="Dashboard Financeiro")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    
    /* Card Geral */
    .stock-card {
        background-color: #262730;
        border: 1px solid #3f3f46;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: transform 0.1s;
    }
    .stock-card:hover { border-color: #71717a; }
    
    /* Área do Logo e Nome */
    .info-container { display: flex; align-items: center; gap: 12px; }
    
    /* LOGO: Usando Google Favicon */
    .logo-img {
        width: 32px; height: 32px;
        border-radius: 50%;
        background-color: #fff; /* Fundo branco ajuda logos transparentes */
        padding: 2px;
    }
    
    /* Textos */
    .ticker { font-weight: bold; font-size: 1rem; color: #fff; display: block; }
    .price { font-size: 0.8rem; color: #a1a1aa; }
    
    /* Badges de % */
    .badge {
        padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 0.9rem; min-width: 60px; text-align: center;
    }
    .up { background-color: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
    .down { background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. DADOS
# ==============================================================================
@st.cache_data(ttl=300)
def get_market_data():
    df = yf.download(LISTA_ACOES, period="2d", progress=False)['Close']
    
    # Cálculos
    var_pct = ((df.iloc[-1] - df.iloc[-2]) / df.iloc[-2]) * 100
    last_price = df.iloc[-1]
    
    # Tabela Final
    final_df = pd.DataFrame({'Var': var_pct, 'Preco': last_price})
    final_df.index = final_df.index.str.replace('.SA', '') # Limpa nome
    
    # Ordenação
    top_high = final_df.sort_values('Var', ascending=False).head(5)
    top_low = final_df.sort_values('Var', ascending=True).head(5)
    
    return top_high, top_low

# ==============================================================================
# 4. FUNÇÃO DE RENDERIZAÇÃO (CARD COM LOGO DO GOOGLE)
# ==============================================================================
def render_stock_card(ticker, row, trend):
    # BUSCA O DOMÍNIO
    domain = EMPRESAS_DOMINIOS.get(ticker, 'google.com')
    
    # -----------------------------------------------------------
    # TRUQUE DO LOGO: Google Favicons API
    # sz=64 define o tamanho. É muito mais estável que Clearbit.
    # -----------------------------------------------------------
    logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    
    style_class = "up" if trend == "up" else "down"
    sign = "+" if trend == "up" else ""
    
    return f"""
    <div class="stock-card">
        <div class="info-container">
            <img src="{logo_url}" class="logo-img" alt="{ticker}">
            <div>
                <span class="ticker">{ticker}</span>
                <span class="price">R$ {row['Preco']:.2f}</span>
            </div>
        </div>
        <div class="badge {style_class}">
            {sign}{row['Var']:.2f}%
        </div>
    </div>
    """

# ==============================================================================
# 5. EXECUÇÃO
# ==============================================================================
st.subheader("⚡ Painel de Monitoramento")

try:
    highs, lows = get_market_data()
    
    col1, col2 = st.columns(2, gap="medium")

    # --- COLUNA ESQUERDA: ALTAS ---
    with col1:
        st.markdown("#### 🚀 Maiores Altas")
        for ticker, row in highs.iterrows():
            st.markdown(render_stock_card(ticker, row, "up"), unsafe_allow_html=True)

    # --- COLUNA DIREITA: BAIXAS ---
    with col2:
        st.markdown("#### 🔻 Maiores Baixas")
        for ticker, row in lows.iterrows():
            st.markdown(render_stock_card(ticker, row, "down"), unsafe_allow_html=True)

    st.divider()
    
    # --- ÁREA LANGCHAIN (PROVISÓRIA) ---
    st.write("🤖 **Assistente IA (LangChain)**")
    prompt = st.text_input("Pergunte sobre o mercado:", placeholder="Ex: Por que a Petrobras caiu hoje?")
    
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")