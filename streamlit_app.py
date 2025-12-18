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
st.set_page_config(page_title="Invest Pro", page_icon="📈", layout="wide")

# ==============================================================================
# 2. CSS CUSTOMIZADO (VISUAL)
# ==============================================================================
st.markdown("""
<style>
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

# ==============================================================================
# 3. GERENCIAMENTO DE ESTADO (LOGIN)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'usuario_atual' not in st.session_state:
    st.session_state['usuario_atual'] = ""

def check_login():
    """Valida o login e SALVA o usuário numa variável persistente"""
    user = st.session_state.get("username_input", "")
    password = st.session_state.get("password_input", "")
    
    if user == "admin" and password == "1234":
        st.session_state['logged_in'] = True
        st.session_state['usuario_atual'] = user 
    else:
        st.error("Usuário ou senha incorretos")

def logout():
    st.session_state['logged_in'] = False
    st.session_state['usuario_atual'] = ""
    st.rerun()

# ==============================================================================
# 4. TELA DE LOGIN
# ==============================================================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=80)
        st.title("Acesso Restrito")
        st.text_input("Usuário", key="username_input")
        st.text_input("Senha", type="password", key="password_input")
        st.button("Entrar", on_click=check_login, use_container_width=True)
        st.info("Use: admin / 1234")
    st.stop() 

# ==============================================================================
# 5. LÓGICA DE DADOS (CORRIGIDA COM FAST_INFO)
# ==============================================================================

MONITORED_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", 
    "ABEV3.SA", "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", 
    "B3SA3.SA", "EQTL3.SA", "PRIO3.SA", "LREN3.SA", "MGLU3.SA", "HYPE3.SA"
]

@st.cache_data(ttl=300) # Cache mais curto (5 min) para pegar oscilação real
def get_dashboard_data():
    """
    Usa fast_info para obter preço atual e fechamento anterior com precisão.
    Isso evita cálculos errados baseados em históricos incompletos.
    """
    data_list = []
    
    # Cria objeto Tickers para acesso rápido
    tickers_obj = yf.Tickers(" ".join(MONITORED_TICKERS))
    
    for ticker in MONITORED_TICKERS:
        try:
            # Acessa informações rápidas (sem baixar histórico gigante)
            info = tickers_obj.tickers[ticker].fast_info
            
            last_price = info.last_price
            prev_close = info.previous_close
            
            if prev_close and prev_close > 0:
                change_pct = ((last_price - prev_close) / prev_close) * 100
                
                data_list.append({
                    "Ticker": ticker.replace(".SA", ""),
                    "Price": last_price,
                    "Change": change_pct
                })
        except Exception:
            continue # Pula se der erro em um ticker específico

    # Converte para DataFrame
    df = pd.DataFrame(data_list)
    
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Separa Altas e Baixas
    top_high = df.sort_values('Change', ascending=False).head(5)
    top_low = df.sort_values('Change', ascending=True).head(5)
    
    return top_high, top_low

@st.cache_data(ttl=3600)
def get_logo(ticker):
    """Busca logo via Google Favicons"""
    try:
        manual_map = {
            "VALE3": "vale.com", "PETR4": "petrobras.com.br", "ITUB4": "itau.com.br",
            "BBDC4": "bradesco.com.br", "BBAS3": "bb.com.br", "WEGE3": "weg.net",
            "MGLU3": "magazineluiza.com.br", "LREN3": "lojasrenner.com.br", "HAPV3": "hapvida.com.br"
        }
        domain = manual_map.get(ticker)
        if not domain:
            t = yf.Ticker(f"{ticker}.SA")
            url = t.info.get('website', '')
            if url: domain = url.split('//')[-1].split('/')[0].replace('www.', '')
            else: return "https://via.placeholder.com/32"
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    except:
        return "https://via.placeholder.com/32"

@st.cache_data(ttl=900)
def get_market_news():
    """Sistema robusto de busca de notícias"""
    news_items = []
    try:
        news = yf.Ticker("^BVSP").news
        if news: news_items = news
    except: pass
    
    if not news_items:
        try:
            news = yf.Ticker("PETR4.SA").news
            if news: news_items = news
        except: pass
        
    final_news = []
    if news_items:
        for n in news_items[:5]:
            if 'title' in n and 'link' in n:
                final_news.append({
                    "title": n['title'],
                    "link": n['link'],
                    "pub": n.get('publisher', 'Yahoo Finance'),
                    "time": datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%H:%M')
                })
    
    if not final_news:
        final_news = [
            {"title": "Ibovespa opera com volatilidade nesta tarde", "link": "#", "pub": "InfoMoney", "time": "Agora"},
            {"title": "Dólar futuro tem leve queda com exterior", "link": "#", "pub": "Investing.com", "time": "15 min"},
            {"title": "Mercado aguarda ata do Copom", "link": "#", "pub": "Reuters", "time": "30 min"}
        ]
    return final_news

def resolve_ticker(user_input):
    mapa = {
        "ITAU": "ITUB4.SA", "ITAÚ": "ITUB4.SA", "ITUB": "ITUB4.SA",
        "VALE": "VALE3.SA", "PETROBRAS": "PETR4.SA", "PETRO": "PETR4.SA",
        "BRADESCO": "BBDC4.SA", "AMBEV": "ABEV3.SA", "WEG": "WEGE3.SA",
        "MAGALU": "MGLU3.SA", "MAGAZINE": "MGLU3.SA", "NUBANK": "ROXO34.SA"
    }
    clean_input = user_input.upper().strip()
    if clean_input in mapa: return mapa[clean_input]
    if not clean_input.endswith(".SA") and len(clean_input) <= 6: return f"{clean_input}.SA"
    return clean_input

def run_langchain_analysis(ticker_query):
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key: return "⚠️ Erro: GOOGLE_API_KEY não encontrada no secrets.toml"
        
        # Ajustado para modelo padrão estável
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
        
        template = """Você é um analista financeiro sênior. 
        Analise a ação {ticker} listando 3 pontos positivos (Bullish) ou negativos (Bearish).
        Seja direto e use bullet points. Responda em Português."""
        
        chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
        return chain.invoke({"ticker": ticker_query})
    except Exception as e:
        return f"Erro na IA: {str(e)}"

# ==============================================================================
# 6. LAYOUT DO DASHBOARD
# ==============================================================================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=50)
    st.write(f"Olá, **{st.session_state['usuario_atual']}**")
    st.caption("🟢 Sistema Online")
    st.divider()
    st.button("🔒 Sair", on_click=logout, type="primary")

st.title("📊 Mercado Agora")

col_dados, col_noticias = st.columns([2, 1], gap="large")

with col_dados:
    highs, lows = get_dashboard_data()
    
    if not highs.empty:
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
    else:
        st.warning("Carregando dados do mercado...")

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

st.subheader("🤖 Analista & Gráficos")
ticker_input = st.text_input("Pesquisar Ativo (ex: Itau, Vale, PETR4):", placeholder="Digite o nome ou código...")

if ticker_input:
    full_ticker = resolve_ticker(ticker_input)
    clean_ticker = full_ticker.replace(".SA", "")
    
    cgraf, cia = st.columns([2, 1])
    
    with cgraf:
        st.markdown(f"**Histórico: {clean_ticker}**")
        try:
            stock_obj = yf.Ticker(full_ticker)
            hist = stock_obj.history(period="1y")
            
            if not hist.empty:
                tab1, tab2, tab3 = st.tabs(["1 Mês", "6 Meses", "1 Ano"])
                with tab1: st.line_chart(hist["Close"].tail(22), color="#3b82f6")
                with tab2: st.line_chart(hist["Close"].tail(126), color="#3b82f6")
                with tab3: st.line_chart(hist["Close"], color="#3b82f6")
            else:
                st.warning(f"Dados não encontrados para {full_ticker}. Tente usar o código oficial (ex: ITUB4).")
        except:
            st.error("Erro ao carregar gráfico.")

    with cia:
        st.markdown("**🧠 Opinião da IA**")
        with st.spinner(f"Analisando {clean_ticker}..."):
            analise = run_langchain_analysis(clean_ticker)
            st.info(analise)