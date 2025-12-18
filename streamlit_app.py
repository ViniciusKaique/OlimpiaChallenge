import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Invest Pro", page_icon="🔒", layout="wide")

# ==============================================================================
# 2. SISTEMA DE LOGIN (SESSION STATE)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login():
    """Verifica usuário e senha"""
    user = st.session_state.get("username_input", "")
    password = st.session_state.get("password_input", "")
    
    # --- CREDENCIAIS (Altere aqui) ---
    if user == "admin" and password == "1234":
        st.session_state['logged_in'] = True
    else:
        st.error("Usuário ou senha incorretos")

def logout():
    st.session_state['logged_in'] = False
    st.rerun()

# ==============================================================================
# 3. TELA DE LOGIN (BLOQUEIO)
# ==============================================================================
if not st.session_state['logged_in']:
    # Centraliza o login usando colunas
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True) # Espaço topo
        st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=80)
        st.title("Acesso Restrito")
        
        st.text_input("Usuário", key="username_input")
        st.text_input("Senha", type="password", key="password_input")
        
        st.button("Entrar", on_click=check_login, use_container_width=True)
        st.info("Use: admin / 1234")
    
    # Interrompe o script aqui se não estiver logado
    st.stop()

# ==============================================================================
# 4. DASHBOARD (SÓ CARREGA SE LOGADO)
# ==============================================================================

# CSS E ESTILOS
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
</style>
""", unsafe_allow_html=True)

# BARRA LATERAL (AGORA COM LOGOUT FUNCIONAL)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=50)
    st.write(f"Olá, **{st.session_state['username_input']}**")
    st.caption("🟢 Sistema Online")
    st.divider()
    # Botão de Sair
    st.button("🔒 Sair do Sistema", on_click=logout, type="primary")

# --- LÓGICA DE DADOS ---
MONITORED_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", 
    "ABEV3.SA", "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", 
    "B3SA3.SA", "EQTL3.SA", "PRIO3.SA", "LREN3.SA", "MGLU3.SA", "HYPE3.SA"
]

@st.cache_data(ttl=600)
def get_dashboard_data():
    df = yf.download(MONITORED_TICKERS, period="2d", progress=False)['Close']
    changes = ((df.iloc[-1] - df.iloc[-2]) / df.iloc[-2]) * 100
    prices = df.iloc[-1]
    data = pd.DataFrame({'Change': changes, 'Price': prices})
    data.index = data.index.str.replace('.SA', '')
    return data.sort_values('Change', ascending=False).head(5), \
           data.sort_values('Change', ascending=True).head(5)

@st.cache_data(ttl=3600)
def get_logo(ticker):
    try:
        t = yf.Ticker(f"{ticker}.SA")
        url = t.info.get('website', '')
        if not url: return "https://via.placeholder.com/32"
        domain = url.split('//')[-1].split('/')[0].replace('www.', '')
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    except:
        return "https://via.placeholder.com/32"

@st.cache_data(ttl=900)
def get_market_news():
    try:
        news = yf.Ticker("^BVSP").news[:6]
        return [{
            "title": n['title'], "link": n['link'], "pub": n['publisher'],
            "time": datetime.fromtimestamp(n['providerPublishTime']).strftime('%H:%M')
        } for n in news]
    except:
        return []

def run_langchain_analysis(ticker_query):
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key: return "⚠️ Configure a GOOGLE_API_KEY no secrets.toml"
        llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key)
        template = "Analise a ação {ticker} em 3 pontos curtos (Bullish/Bearish) para um day trader."
        chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
        return chain.invoke({"ticker": ticker_query})
    except Exception as e:
        return f"Erro IA: {str(e)}"

# --- RENDERIZAÇÃO DO LAYOUT ---

st.title("📊 Mercado Agora")

col_dados, col_noticias = st.columns([2, 1], gap="large")

# GRID DE ALTAS E BAIXAS
with col_dados:
    highs, lows = get_dashboard_data()
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 🚀 Maiores Altas")
        for ticker, row in highs.iterrows():
            logo = get_logo(ticker)
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
            logo = get_logo(ticker)
            st.markdown(f"""
            <div class="stock-card">
                <div style="display:flex; align-items:center">
                    <img src="{logo}" class="logo-img">
                    <div><b>{ticker}</b><br><span style="font-size:12px; color:#aaa">R$ {row['Price']:.2f}</span></div>
                </div>
                <div class="txt-red">{row['Change']:.2f}%</div>
            </div>""", unsafe_allow_html=True)

# LISTA DE NOTÍCIAS
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
        </a>""", unsafe_allow_html=True)

st.divider()

# ÁREA DE ANÁLISE E GRÁFICOS
st.subheader("🤖 Analista & Gráficos")
ticker_input = st.text_input("Pesquisar Ativo (ex: PETR4):", placeholder="Digite o código...")

if ticker_input:
    clean_ticker = ticker_input.upper().replace(".SA", "")
    full_ticker = f"{clean_ticker}.SA"
    
    cgraf, cia = st.columns([2, 1])
    
    with cgraf:
        st.markdown(f"**Histórico: {clean_ticker}**")
        tab1, tab2, tab3 = st.tabs(["1 Mês", "6 Meses", "1 Ano"])
        stock_obj = yf.Ticker(full_ticker)
        
        with tab1: st.line_chart(stock_obj.history(period="1mo")["Close"], color="#3b82f6")
        with tab2: st.line_chart(stock_obj.history(period="6mo")["Close"], color="#3b82f6")
        with tab3: st.line_chart(stock_obj.history(period="1y")["Close"], color="#3b82f6")

    with cia:
        st.markdown("**🧠 Opinião da IA**")
        with st.spinner("Analisando..."):
            analise = run_langchain_analysis(clean_ticker)
            st.info(analise)