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
# 1. CONFIGURAÇÃO VISUAL
# ==============================================================================
st.set_page_config(page_title="Invest Pro", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
    /* Cards de Ações */
    .stock-card {
        background-color: #262730;
        border: 1px solid #3f3f46;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .logo-img {
        width: 32px; height: 32px; border-radius: 50%; 
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
        border-left: 4px solid #3b82f6;
        transition: transform 0.2s;
        text-decoration: none;
        display: block;
    }
    .news-card:hover { transform: translateX(5px); background-color: #374151; }
    .news-title { font-size: 0.9rem; color: #f3f4f6; font-weight: 500; margin-bottom: 4px; }
    .news-meta { font-size: 0.75rem; color: #9ca3af; }
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
    st.rerun()

if not st.session_state['logged_in']:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🔒 Acesso Restrito")
        st.text_input("Usuário", key="username_input")
        st.text_input("Senha", type="password", key="password_input")
        st.button("Entrar", on_click=check_login, use_container_width=True)
        st.info("Login: admin | Senha: 1234")
    st.stop()

# ==============================================================================
# 3. FUNÇÕES DE DADOS (CORRIGIDAS)
# ==============================================================================

MONITORED_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", 
    "ABEV3.SA", "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", 
    "B3SA3.SA", "EQTL3.SA", "PRIO3.SA", "LREN3.SA", "MGLU3.SA", "HYPE3.SA"
]

@st.cache_data(ttl=120) # Cache curto (2 min) para garantir preço fresco
def get_dashboard_data():
    """Usa fast_info para pegar variação exata baseada no fechamento anterior"""
    data = []
    
    # Baixa objetos Ticker em lote (mais rápido)
    tickers = yf.Tickers(" ".join(MONITORED_TICKERS))
    
    for symbol in MONITORED_TICKERS:
        try:
            # fast_info acessa dados brutos da bolsa sem processamento de histórico
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
def get_google_news():
    """Busca notícias via RSS do Google News (Muito mais estável que Yahoo)"""
    url = "https://news.google.com/rss/search?q=Mercado+Financeiro+Brasil+when:1d&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        news_list = []
        
        for item in root.findall('.//item')[:6]:
            title = item.find('title').text
            # Limpa o título (Remove o nome do jornal no final se tiver)
            source = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                source = parts[1]
                
            news_list.append({
                "title": title,
                "link": item.find('link').text,
                "source": source,
                "time": item.find('pubDate').text[17:22] # Hora HH:MM
            })
        return news_list
    except:
        return [{"title": "Erro ao carregar notícias do Google", "link": "#", "source": "Sistema", "time": "--:--"}]

@st.cache_data(ttl=3600)
def get_logo(ticker):
    """Busca logo via Google Favicons baseado em dicionário de sites"""
    map_sites = {
        "VALE3": "vale.com", "PETR4": "petrobras.com.br", "ITUB4": "itau.com.br",
        "BBDC4": "bradesco.com.br", "BBAS3": "bb.com.br", "WEGE3": "weg.net",
        "MGLU3": "magazineluiza.com.br", "LREN3": "lojasrenner.com.br", "HAPV3": "hapvida.com.br",
        "SUZB3": "suzano.com.br", "BPAC11": "btgpactual.com", "RDOR3": "rededorsaoluiz.com.br",
        "EQTL3": "equatorialenergia.com.br", "PRIO3": "prio3.com.br", "B3SA3": "b3.com.br"
    }
    domain = map_sites.get(ticker, "google.com")
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"

def resolve_ticker(text):
    """Corrige nomes comuns para Tickers da Bolsa"""
    mapa = {
        "ITAU": "ITUB4.SA", "ITAÚ": "ITUB4.SA", "ITUB": "ITUB4.SA",
        "VALE": "VALE3.SA", "PETROBRAS": "PETR4.SA", "PETRO": "PETR4.SA", "PETR4": "PETR4.SA",
        "BRADESCO": "BBDC4.SA", "AMBEV": "ABEV3.SA", "WEG": "WEGE3.SA",
        "MAGALU": "MGLU3.SA", "MAGAZINE": "MGLU3.SA", "NUBANK": "ROXO34.SA"
    }
    clean = text.upper().strip()
    if clean in mapa: return mapa[clean]
    # Se digitar só WEGE3, adiciona .SA
    if len(clean) <= 6 and not clean.endswith(".SA"): return f"{clean}.SA"
    return clean

def run_gemini_analysis(ticker):
    """Analista IA (Atualizado para Gemini 1.5 Flash)"""
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key: return "⚠️ Configure a API Key no arquivo .streamlit/secrets.toml"
        
        # Modelo atualizado e mais rápido
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
        
        template = """Você é um analista financeiro experiente.
        Analise a ação {ticker} e forneça 3 pontos cruciais (Positivos ou Negativos) para um investidor hoje.
        Seja direto, use bullet points e fale em Português."""
        
        chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
        return chain.invoke({"ticker": ticker})
    except Exception as e:
        return f"Erro na IA: {str(e)}"

# ==============================================================================
# 4. DASHBOARD
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
            st.info("Carregando dados...")

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
    news = get_google_news()
    for n in news:
        st.markdown(f"""
        <a href="{n['link']}" target="_blank" class="news-card">
            <div class="news-title">{n['title']}</div>
            <div class="news-meta">{n['source']} • {n['time']}</div>
        </a>""", unsafe_allow_html=True)

st.divider()

# Área de Análise
st.subheader("🤖 Analista IA & Gráficos")
search_input = st.text_input("Pesquisar Ativo (ex: Itau, Vale):", placeholder="Digite o nome ou código...")

if search_input:
    # Resolve o nome para Ticker oficial
    ticker_oficial = resolve_ticker(search_input)
    ticker_display = ticker_oficial.replace(".SA", "")
    
    cg, cia = st.columns([2, 1])
    
    with cg:
        st.markdown(f"**Gráfico: {ticker_display}**")
        try:
            stock = yf.Ticker(ticker_oficial)
            # Pega 1 ano de histórico para garantir que o gráfico não fique vazio
            hist = stock.history(period="1y")
            
            if not hist.empty:
                st.line_chart(hist['Close'], color="#3b82f6")
            else:
                st.warning(f"Não foram encontrados dados recentes para {ticker_oficial}. Tente outro ativo.")
        except Exception as e:
            st.error(f"Erro ao carregar gráfico: {e}")
            
    with cia:
        st.markdown(f"**Análise Inteligente**")
        with st.spinner(f"Analisando {ticker_display}..."):
            analise = run_gemini_analysis(ticker_display)
            st.info(analise)