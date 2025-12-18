import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==============================================================================
# 1. CONFIGURAÇÃO E CSS
# ==============================================================================
st.set_page_config(page_title="Invest AI Dashboard", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    /* Ajustes Gerais */
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
    /* Cards de Ações */
    .stock-card {
        background-color: #262730;
        border: 1px solid #3f3f46;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .logo-img {
        width: 28px; height: 28px; border-radius: 50%; 
        background-color: #fff; padding: 2px; margin-right: 10px;
    }
    .stock-val { font-weight: bold; font-size: 0.9rem; }
    
    /* Cores de Alta e Baixa */
    .txt-green { color: #4ade80; font-weight: bold; }
    .txt-red { color: #f87171; font-weight: bold; }
    
    /* Notícias */
    .news-card {
        background-color: #1f2937;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
        border-left: 3px solid #3b82f6;
        transition: background 0.2s;
    }
    .news-card:hover { background-color: #374151; }
    .news-title { font-size: 0.85rem; color: #e5e7eb; font-weight: 500; text-decoration: none; }
    .news-time { font-size: 0.7rem; color: #9ca3af; margin-top: 4px; display: block; }

    /* Input Langchain */
    .stTextInput input { border-radius: 10px; border: 1px solid #4b5563; }
</style>
""", unsafe_allow_html=True)

# Lista base para monitoramento
MONITORED_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", 
    "ABEV3.SA", "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", 
    "B3SA3.SA", "EQTL3.SA", "PRIO3.SA", "LREN3.SA", "MGLU3.SA", "HYPE3.SA"
]

# ==============================================================================
# 2. SIDEBAR (LOGIN)
# ==============================================================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=60)
    st.markdown("### Bem-vindo, **User**")
    st.markdown("---")
    st.caption("Status: 🟢 Online")
    st.caption(f"Atualizado: {datetime.now().strftime('%H:%M')}")
    st.markdown("---")
    if st.button("Sair / Logout"):
        st.warning("Função de logout simulada.")

# ==============================================================================
# 3. FUNÇÕES DE DADOS E LANGCHAIN
# ==============================================================================

@st.cache_data(ttl=600)
def get_dashboard_data():
    """Baixa dados em lote e processa altas/baixas"""
    df = yf.download(MONITORED_TICKERS, period="2d", progress=False)['Close']
    
    # Variação %
    changes = ((df.iloc[-1] - df.iloc[-2]) / df.iloc[-2]) * 100
    prices = df.iloc[-1]
    
    data = pd.DataFrame({'Change': changes, 'Price': prices})
    data.index = data.index.str.replace('.SA', '')
    
    return data.sort_values('Change', ascending=False).head(5), \
           data.sort_values('Change', ascending=True).head(5)

@st.cache_data(ttl=3600) # Cache longo para não ficar lento
def get_logo(ticker):
    """Tenta descobrir o site oficial via Yahoo para pegar o Favicon"""
    try:
        # Sem lista fixa: consulta metadados do Yahoo (pode demorar na 1ª vez)
        t = yf.Ticker(f"{ticker}.SA")
        url = t.info.get('website', '')
        if not url: return "https://via.placeholder.com/32"
        
        # Extrai domínio limpo (ex: https://www.vale.com -> vale.com)
        domain = url.split('//')[-1].split('/')[0].replace('www.', '')
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    except:
        return "https://via.placeholder.com/32"

@st.cache_data(ttl=900)
def get_market_news():
    """Pega notícias do Ibovespa"""
    try:
        news = yf.Ticker("^BVSP").news[:5]
        return [{
            "title": n['title'], 
            "link": n['link'], 
            "pub": n['publisher'],
            "time": datetime.fromtimestamp(n['providerPublishTime']).strftime('%H:%M')
        } for n in news]
    except:
        return []

def run_langchain_analysis(ticker_query):
    """Executa a análise via Gemini"""
    try:
        # Tenta pegar a chave do st.secrets ou usa placeholder para não quebrar
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            return "⚠️ Erro: Configure a GOOGLE_API_KEY no .streamlit/secrets.toml"
        
        llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key)
        template = "Atue como um analista sênior. Resuma a situação atual de {ticker} em 3 pontos curtos (Bullish/Bearish)."
        chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
        return chain.invoke({"ticker": ticker_query})
    except Exception as e:
        return f"Erro na IA: {str(e)}"

# ==============================================================================
# 4. RENDERIZAÇÃO DA PÁGINA
# ==============================================================================

# --- PARTE SUPERIOR: GRID DASHBOARD ---
st.title("📊 Mercado Hoje")

col_dados, col_noticias = st.columns([2, 1], gap="large")

# COLUNA DA ESQUERDA: ALTAS E BAIXAS
with col_dados:
    highs, lows = get_dashboard_data()
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 🚀 Maiores Altas")
        for ticker, row in highs.iterrows():
            logo = get_logo(ticker) # Puxa dinâmico
            st.markdown(f"""
            <div class="stock-card">
                <div style="display:flex; align-items:center">
                    <img src="{logo}" class="logo-img">
                    <div><b>{ticker}</b><br><span style="font-size:12px; color:#aaa">R$ {row['Price']:.2f}</span></div>
                </div>
                <div class="txt-green">+{row['Change']:.2f}%</div>
            </div>""", unsafe_allow_html=True)
            
    with c2:
        st.markdown("#### 🔻 Maiores Baixas")
        for ticker, row in lows.iterrows():
            logo = get_logo(ticker) # Puxa dinâmico
            st.markdown(f"""
            <div class="stock-card">
                <div style="display:flex; align-items:center">
                    <img src="{logo}" class="logo-img">
                    <div><b>{ticker}</b><br><span style="font-size:12px; color:#aaa">R$ {row['Price']:.2f}</span></div>
                </div>
                <div class="txt-red">{row['Change']:.2f}%</div>
            </div>""", unsafe_allow_html=True)

# COLUNA DA DIREITA: NOTÍCIAS
with col_noticias:
    st.markdown("#### 📰 Manchetes")
    news_list = get_market_news()
    for n in news_list:
        st.markdown(f"""
        <a href="{n['link']}" target="_blank" style="text-decoration:none;">
            <div class="news-card">
                <div class="news-title">{n['title']}</div>
                <span class="news-time">{n['pub']} • {n['time']}</span>
            </div>
        </a>
        """, unsafe_allow_html=True)

st.markdown("---")

# --- PARTE INFERIOR: LANGCHAIN + GRÁFICOS ---
st.subheader("🤖 Analista IA & Gráficos")

# Input do usuário
ticker_input = st.text_input("Digite o Ticker para análise (ex: PETR4, VALE3):", placeholder="Busque um ativo...")

if ticker_input:
    clean_ticker = ticker_input.upper().replace(".SA", "")
    full_ticker = f"{clean_ticker}.SA"
    
    # Container Flexível
    c_grafico, c_ia = st.columns([2, 1])
    
    with c_grafico:
        st.markdown(f"#### Histórico: {clean_ticker}")
        
        # Abas de tempo
        tab1, tab2, tab3 = st.tabs(["1 Mês", "6 Meses", "1 Ano"])
        
        # Pega dados históricos
        stock_obj = yf.Ticker(full_ticker)
        
        with tab1:
            hist_1m = stock_obj.history(period="1mo")
            st.line_chart(hist_1m["Close"], color="#3b82f6")
        
        with tab2:
            hist_6m = stock_obj.history(period="6mo")
            st.line_chart(hist_6m["Close"], color="#3b82f6")
            
        with tab3:
            hist_1y = stock_obj.history(period="1y")
            st.line_chart(hist_1y["Close"], color="#3b82f6")

    with c_ia:
        st.markdown("#### 🧠 Análise Gemini")
        with st.spinner("Consultando IA..."):
            # Chama a função LangChain definida acima
            analise = run_langchain_analysis(clean_ticker)
            
            st.info(analise)
            
            # Dados fundamentais rápidos
            info = stock_obj.fast_info
            st.markdown(f"""
            **Preço:** {info.last_price:.2f}
            **Cap. Mercado:** {info.market_cap/1e9:.1f}B
            """)