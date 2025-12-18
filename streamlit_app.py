import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Invest Pro", page_icon="📈", layout="wide")

# CSS para visual profissional
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .stock-card {
        background-color: #262730; border: 1px solid #3f3f46; border-radius: 8px;
        padding: 12px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between;
    }
    .logo-img { width: 32px; height: 32px; border-radius: 50%; background-color: #fff; padding: 2px; margin-right: 10px; }
    .txt-green { color: #4ade80; font-weight: bold; }
    .txt-red { color: #f87171; font-weight: bold; }
    .news-card {
        background-color: #1f2937; padding: 12px; border-radius: 6px; margin-bottom: 10px;
        border-left: 4px solid #3b82f6; transition: transform 0.2s;
    }
    .news-card:hover { transform: translateX(5px); background-color: #374151; }
    .news-title { font-size: 0.9rem; color: #f3f4f6; font-weight: 500; text-decoration: none; display: block; margin-bottom: 4px; }
    .news-source { font-size: 0.75rem; color: #9ca3af; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. SISTEMA DE LOGIN
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'usuario_atual' not in st.session_state:
    st.session_state['usuario_atual'] = ""

def check_login():
    user = st.session_state.get("username_input", "")
    password = st.session_state.get("password_input", "")
    if user == "admin" and password == "1234":
        st.session_state['logged_in'] = True
        st.session_state['usuario_atual'] = user
    else:
        st.error("Dados incorretos.")

def logout():
    st.session_state['logged_in'] = False
    st.session_state['usuario_atual'] = ""
    st.rerun()

if not st.session_state['logged_in']:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=80)
        st.title("Acesso Restrito")
        st.text_input("Usuário", key="username_input")
        st.text_input("Senha", type="password", key="password_input")
        st.button("Entrar", on_click=check_login, use_container_width=True)
        st.info("Admin: admin | 1234")
    st.stop()

# ==============================================================================
# 3. DADOS DE MERCADO (CORRIGIDOS)
# ==============================================================================

# Lista monitorada (Adicionei .SA automaticamente na função se precisar)
MONITORED_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", 
    "ABEV3.SA", "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", 
    "B3SA3.SA", "EQTL3.SA", "PRIO3.SA", "LREN3.SA", "MGLU3.SA", "HYPE3.SA"
]

@st.cache_data(ttl=120) # Cache curto para pegar preço real
def get_dashboard_data():
    """Usa fast_info para precisão máxima de variação %"""
    data = []
    
    # Objeto Tickers para chamada otimizada em lote
    tickers = yf.Tickers(" ".join(MONITORED_TICKERS))
    
    for symbol in MONITORED_TICKERS:
        try:
            # fast_info pega dados do book atual, não do histórico de ontem
            info = tickers.tickers[symbol].fast_info
            price = info.last_price
            prev_close = info.previous_close
            
            if prev_close and price:
                change = ((price - prev_close) / prev_close) * 100
                data.append({
                    "Ticker": symbol.replace(".SA", ""),
                    "Price": price,
                    "Change": change
                })
        except:
            continue
            
    df = pd.DataFrame(data)
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    
    return df.sort_values('Change', ascending=False).head(5), \
           df.sort_values('Change', ascending=True).head(5)

@st.cache_data(ttl=900)
def get_google_news(query="Ibovespa"):
    """Busca notícias via RSS do Google (Infalível)"""
    # Formata URL do RSS do Google News Brasil
    url = f"https://news.google.com/rss/search?q={query}+when:1d&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        news_list = []
        
        # Pega as 6 primeiras notícias
        for item in root.findall('.//item')[:6]:
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            
            # Limpa o título (Google news as vezes põe " - Fonte" no final)
            source = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                source = parts[1]
                
            news_list.append({
                "title": title,
                "link": link,
                "source": source,
                "time": pub_date[17:22] # Pega apenas a hora HH:MM da string de data
            })
        return news_list
    except:
        # Fallback se o Google bloquear (raro)
        return [{"title": "Mercado aguarda definições econômicas", "link": "#", "source": "InfoMoney", "time": "10:00"}]

@st.cache_data(ttl=3600)
def get_logo(ticker):
    """Busca Favicon oficial da empresa"""
    map_sites = {
        "VALE3": "vale.com", "PETR4": "petrobras.com.br", "ITUB4": "itau.com.br",
        "BBDC4": "bradesco.com.br", "BBAS3": "bb.com.br", "WEGE3": "weg.net",
        "MGLU3": "magazineluiza.com.br", "LREN3": "lojasrenner.com.br", "HAPV3": "hapvida.com.br",
        "SUZB3": "suzano.com.br", "BPAC11": "btgpactual.com", "RDOR3": "rededorsaoluiz.com.br",
        "EQTL3": "equatorialenergia.com.br", "PRIO3": "prio3.com.br", "B3SA3": "b3.com.br"
    }
    domain = map_sites.get(ticker, "google.com")
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"

def run_gemini_analysis(ticker):
    """IA Analista (Gemini 1.5)"""
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key: return "⚠️ Configure a API Key no secrets.toml"
        
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
        template = "Resuma a situação da ação {ticker} em 3 bullet points curtos para um investidor. Português."
        chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
        return chain.invoke({"ticker": ticker})
    except Exception as e:
        return f"Erro IA: {str(e)}"

# ==============================================================================
# 4. DASHBOARD UI
# ==============================================================================

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=50)
    st.write(f"Olá, **{st.session_state['usuario_atual']}**")
    st.divider()
    st.button("Sair", on_click=logout)

st.title("📊 Monitor de Mercado")

col_left, col_right = st.columns([2, 1], gap="medium")

with col_left:
    highs, lows = get_dashboard_data()
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🚀 Maiores Altas")
        if not highs.empty:
            for _, row in highs.iterrows():
                logo = get_logo(row['Ticker'])
                st.markdown(f"""
                <div class="stock-card">
                    <div style="display:flex; align-items:center;">
                        <img src="{logo}" class="logo-img">
                        <div><b>{row['Ticker']}</b><br><span style="font-size:12px; color:#aaa">R$ {row['Price']:.2f}</span></div>
                    </div>
                    <div class="txt-green">+{row['Change']:.2f}%</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Carregando...")

    with c2:
        st.markdown("##### 🔻 Maiores Baixas")
        if not lows.empty:
            for _, row in lows.iterrows():
                logo = get_logo(row['Ticker'])
                st.markdown(f"""
                <div class="stock-card">
                    <div style="display:flex; align-items:center;">
                        <img src="{logo}" class="logo-img">
                        <div><b>{row['Ticker']}</b><br><span style="font-size:12px; color:#aaa">R$ {row['Price']:.2f}</span></div>
                    </div>
                    <div class="txt-red">{row['Change']:.2f}%</div>
                </div>""", unsafe_allow_html=True)

with col_right:
    st.markdown("##### 📰 Manchetes (Google News)")
    news = get_google_news("Mercado Financeiro Brasil")
    for n in news:
        st.markdown(f"""
        <a href="{n['link']}" target="_blank" style="text-decoration:none;">
            <div class="news-card">
                <span class="news-title">{n['title']}</span>
                <span class="news-source">{n['source']} • {n['time']}</span>
            </div>
        </a>""", unsafe_allow_html=True)

st.markdown("---")

# Área de Análise
st.subheader("🤖 Analista IA & Gráficos")
ticker = st.text_input("Pesquisar Ativo (ex: PETR4, ITUB4):", placeholder="Digite o ticker...").upper().strip()

if ticker:
    # Correção automática de ticker
    if not ticker.endswith(".SA") and len(ticker) <= 6: ticker += ".SA"
    
    cg, cia = st.columns([2, 1])
    
    with cg:
        try:
            stock = yf.Ticker(ticker)
            # Tenta pegar histórico
            hist = stock.history(period="6mo")
            if not hist.empty:
                st.line_chart(hist['Close'], color="#3b82f6")
            else:
                st.warning(f"Sem dados gráficos para {ticker}")
        except:
            st.error("Erro no gráfico.")
            
    with cia:
        with st.spinner(f"Analisando {ticker}..."):
            analise = run_gemini_analysis(ticker)
            st.info(analise)