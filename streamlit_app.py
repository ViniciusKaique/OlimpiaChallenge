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
st.set_page_config(page_title="Invest Pro - Análise Automática", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
    /* Cards de Ações (Dashboard) */
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
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 4px solid #3b82f6;
        transition: transform 0.2s;
        text-decoration: none;
        display: block;
    }
    .news-card:hover { transform: translateX(5px); background-color: #374151; }
    .news-title { font-size: 1rem; color: #f3f4f6; font-weight: 600; margin-bottom: 6px; }
    .news-meta { font-size: 0.8rem; color: #9ca3af; display: flex; justify-content: space-between; }
    
    /* Box da IA */
    .ai-box {
        background-color: #2d2d2d;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #444;
    }
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
        st.title("🔒 Invest Banking Access")
        st.text_input("Usuário", key="username_input")
        st.text_input("Senha", type="password", key="password_input")
        st.button("Entrar", on_click=check_login, use_container_width=True)
        st.info("Login: admin | Senha: 1234")
    st.stop()

# ==============================================================================
# 3. FUNÇÕES DE DADOS (DASHBOARD & PESQUISA)
# ==============================================================================

MONITORED_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", 
    "ABEV3.SA", "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", 
    "B3SA3.SA", "EQTL3.SA", "PRIO3.SA", "LREN3.SA", "MGLU3.SA", "HYPE3.SA"
]

@st.cache_data(ttl=120) 
def get_dashboard_data():
    """Usa fast_info para pegar variação exata baseada no fechamento anterior"""
    data = []
    tickers = yf.Tickers(" ".join(MONITORED_TICKERS))
    
    for symbol in MONITORED_TICKERS:
        try:
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
def get_google_news(query="Mercado Financeiro Brasil"):
    """
    Busca notícias via RSS do Google News.
    Aceita uma 'query' para buscar notícias específicas da empresa pesquisada.
    """
    # URL encoded para garantir que espaços funcionem
    query_url = query.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query_url}+when:2d&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    
    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        news_list = []
        
        # Pega até 4 notícias
        for item in root.findall('.//item')[:4]:
            title = item.find('title').text
            source = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                source = parts[1]
                
            news_list.append({
                "title": title,
                "link": item.find('link').text,
                "source": source,
                "time": item.find('pubDate').text[17:22]
            })
        return news_list
    except:
        return []

@st.cache_data(ttl=3600)
def get_logo(ticker):
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
    """Mapeia nomes comuns para Tickers"""
    mapa = {
        "ITAU": "ITUB4.SA", "ITAÚ": "ITUB4.SA", "ITUB": "ITUB4.SA",
        "BRADESCO": "BBDC4.SA", "BBDC": "BBDC4.SA",
        "BANCO DO BRASIL": "BBAS3.SA", "BB": "BBAS3.SA",
        "VALE": "VALE3.SA", "PETROBRAS": "PETR4.SA", "PETRO": "PETR4.SA",
        "SUZANO": "SUZB3.SA", "GERDAU": "GGBR4.SA", "PRIO": "PRIO3.SA",
        "ELETROBRAS": "ELET3.SA", "MAGALU": "MGLU3.SA", "AMBEV": "ABEV3.SA",
        "WEG": "WEGE3.SA", "B3": "B3SA3.SA", "JBS": "JBSS3.SA"
    }
    clean = text.upper().strip()
    if clean in mapa: return mapa[clean]
    if len(clean) <= 6 and not clean.endswith(".SA"): return f"{clean}.SA"
    return clean

# ==============================================================================
# 4. LANGCHAIN (ATUALIZADO PARA O DESAFIO)
# ==============================================================================
def run_langchain_analysis(ticker_symbol, company_name):
    """
    Fluxo LangChain para atender os requisitos:
    A. Resumo/Descrição (Setor, Histórico, Produtos)
    B. Análise Fundamentalista
    """
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key: return "⚠️ Configure a API Key no arquivo secrets.toml"
        
        # Modelo 1.5 Flash (Rápido e Eficiente)
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
        
        # Prompt Engenharia alinhada ao Desafio
        template = """
        Você é um analista de Investment Banking.
        Realize uma pesquisa e gere um relatório conciso sobre a empresa: {company_name} (Ticker: {ticker}).
        
        A saída deve conter OBRIGATORIAMENTE os seguintes tópicos formatados em Markdown:

        ### 1. Resumo Corporativo
        * **Setor:** [Insira o setor]
        * **Descrição:** [Breve histórico e o que a empresa faz]
        * **Principais Produtos/Serviços:** [Liste os principais]

        ### 2. Análise de Mercado (Pontos Chave)
        * Forneça 3 pontos de atenção (Bullish/Otimista ou Bearish/Pessimista) para o momento atual da empresa.

        Seja profissional, direto e utilize Português do Brasil.
        """
        
        chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
        return chain.invoke({"ticker": ticker_symbol, "company_name": company_name})
    except Exception as e:
        return f"Erro na IA: {str(e)}"

# ==============================================================================
# 5. DASHBOARD UI
# ==============================================================================

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/295/295128.png", width=50)
    st.write(f"Analista: **{st.session_state['usuario_atual']}**")
    st.divider()
    st.button("Sair", on_click=logout)

st.title("📊 Monitor de Mercado & Pesquisa")

# --- TOPO: RESUMO GERAL DO MERCADO ---
col_left, col_right = st.columns([2, 1], gap="medium")

with col_left:
    highs, lows = get_dashboard_data()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🚀 Maiores Altas (Dia)")
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

    with c2:
        st.markdown("##### 🔻 Maiores Baixas (Dia)")
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
    st.markdown("##### 📰 Giro de Mercado")
    news = get_google_news("Bolsa de Valores Brasil")
    for n in news:
        st.markdown(f"""
        <a href="{n['link']}" target="_blank" class="news-card">
            <div class="news-title">{n['title']}</div>
            <div class="news-meta">{n['source']} • {n['time']}</div>
        </a>""", unsafe_allow_html=True)

st.markdown("---")

# --- ÁREA DO DESAFIO: PESQUISA & LANGCHAIN ---
st.subheader("🔎 Pesquisa de Ativo (Desafio IB)")
search_input = st.text_input("Digite o nome da empresa (ex: Vale, Itau, Ambev):", placeholder="Nome ou Ticker...").strip()

if search_input:
    # 1. Identificação
    ticker_oficial = resolve_ticker(search_input)
    ticker_display = ticker_oficial.replace(".SA", "")
    
    st.info(f"Processando análise para: **{ticker_display}** ({ticker_oficial})...")

    # 2. Dados via yfinance (Preço e Histórico)
    try:
        stock = yf.Ticker(ticker_oficial)
        info = stock.fast_info
        current_price = info.last_price
        
        # Se não tiver preço, o ticker provavelmente está errado
        if not current_price:
            st.error(f"Não foi possível encontrar dados para '{search_input}'. Tente outro nome.")
            st.stop()
            
    except Exception:
        st.error("Erro ao conectar com a bolsa.")
        st.stop()

    # --- LAYOUT DE RESULTADO DO DESAFIO ---
    
    # Exibe o PREÇO ATUAL (Requisito C do Desafio)
    st.metric(label=f"Preço Atual ({ticker_display})", value=f"R$ {current_price:.2f}")

    col_grafico, col_relatorio = st.columns([1.5, 1])

    with col_grafico:
        st.markdown("#### 📈 Performance da Ação")
        # Abas para 1 mês, 6 meses e 1 ano
        tab1, tab2, tab3 = st.tabs(["1 Mês", "6 Meses", "1 Ano"])
        
        with tab1:
            st.line_chart(stock.history(period="1mo")['Close'], color="#3b82f6")
        with tab2:
            st.line_chart(stock.history(period="6mo")['Close'], color="#3b82f6")
        with tab3:
            st.line_chart(stock.history(period="1y")['Close'], color="#3b82f6")

        # --- NOTÍCIAS ESPECÍFICAS (Requisito B do Desafio) ---
        st.markdown("#### 📰 Últimas Notícias Relevantes")
        # Busca notícias usando o nome digitado + 'ações' para filtrar bem
        company_news = get_google_news(f"{search_input} ações negócios")
        
        if company_news:
            for n in company_news:
                st.markdown(f"""
                <a href="{n['link']}" target="_blank" class="news-card">
                    <div class="news-title">{n['title']}</div>
                    <div class="news-meta">{n['source']} • {n['time']}</div>
                </a>""", unsafe_allow_html=True)
        else:
            st.warning("Nenhuma notícia recente encontrada para esta empresa específica.")

    with col_relatorio:
        st.markdown("#### 🤖 Relatório LangChain (Requisito A)")
        with st.container(border=True):
            with st.spinner("Gerando Resumo e Análise Fundamentalista..."):
                # Roda o LangChain para gerar Descrição e Pontos
                analise = run_langchain_analysis(ticker_oficial, search_input)
                st.markdown(analise)