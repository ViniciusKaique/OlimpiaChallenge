import streamlit as st
import yfinance as yf
from duckduckgo_search import DDGS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import pandas as pd

# ==============================================================================
# 🎨 1. CSS ESTILO "STATUS INVEST"
# ==============================================================================
st.set_page_config(page_title="Status Invest AI", page_icon="📈", layout="wide")

st.markdown("""
<style>
    /* Fundo Geral */
    .stApp { background-color: #F7F9FA; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Esconder Menu Padrão */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}

    /* Card Branco Padrão */
    .invest-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #E6E6E6;
        margin-bottom: 15px;
    }

    /* Títulos */
    h1, h2, h3, h4 { color: #00294F !important; font-weight: 700; }
    
    /* Input de Pesquisa */
    .stTextInput input {
        border-radius: 20px;
        border: 1px solid #ddd;
        padding: 10px 20px;
    }

    /* Estilo dos Mini-Cards (Altas e Baixas) */
    .stock-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        border-bottom: 1px solid #f0f0f0;
        transition: background 0.2s;
    }
    .stock-row:hover { background-color: #f9f9f9; }
    
    .ticker-badge {
        font-weight: bold;
        color: #333;
        font-size: 14px;
        background: #eee;
        padding: 4px 8px;
        border-radius: 4px;
    }
    
    .price-val { font-weight: 600; color: #00294F; }
    
    .up-tag { color: #00C853; font-weight: bold; background: #E8F5E9; padding: 2px 6px; border-radius: 4px; font-size: 0.9em;}
    .down-tag { color: #D50000; font-weight: bold; background: #FFEBEE; padding: 2px 6px; border-radius: 4px; font-size: 0.9em;}

    /* Botões */
    .stButton button {
        background-color: #FFB300; /* Amarelo Status Invest */
        color: black;
        font-weight: bold;
        border: none;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🛠️ 2. MOTOR DE DADOS (YFINANCE + SIMULAÇÃO DE DASHBOARD)
# ==============================================================================

@st.cache_data(ttl=300)
def get_market_overview():
    """
    Simula o painel de 'Altas e Baixas' monitorando as principais ações do IBOV.
    O yfinance não dá a lista da bolsa toda, então monitoramos uma carteira fixa.
    """
    # Lista de ações populares para monitorar no dashboard
    tickers = ["VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "WEGE3.SA", 
               "MGLU3.SA", "BBAS3.SA", "RENT3.SA", "PRIO3.SA", "HAPV3.SA", "ABEV3.SA"]
    
    data_list = []
    
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            # Pega dados rápidos
            price = stock.fast_info.last_price
            prev = stock.fast_info.previous_close
            
            if price and prev:
                change = ((price - prev) / prev) * 100
                data_list.append({
                    "Ticker": t.replace(".SA", ""),
                    "Preço": price,
                    "Var": change
                })
        except:
            continue
            
    df = pd.DataFrame(data_list)
    
    # Separa Altas e Baixas
    altas = df[df["Var"] >= 0].sort_values(by="Var", ascending=False).head(5)
    baixas = df[df["Var"] < 0].sort_values(by="Var", ascending=True).head(5)
    
    return altas, baixas

@st.cache_data(ttl=120)
def get_stock_details(ticker):
    """Pega detalhes específicos de uma ação pesquisada."""
    if not ticker: return None
    clean = ticker.upper().strip()
    if not clean.endswith(".SA") and len(clean) <= 6: clean += ".SA"
    
    try:
        stock = yf.Ticker(clean)
        info = stock.fast_info
        return {
            "ticker": clean.replace(".SA",""),
            "price": info.last_price,
            "change": ((info.last_price - info.previous_close)/info.previous_close)*100
        }
    except:
        return None

def get_web_search_direct(query):
    """Busca com DDGS garantindo links para o PDF."""
    text_results = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, region='br-pt', safesearch='off', max_results=4))
            for r in results:
                # Estrutura clara para o Gemini entender que isso é uma fonte
                text_results += f"TITULO: {r['title']} | LINK: {r['url']} | FONTE: {r['source']}\n"
    except Exception as e:
        text_results = f"Erro busca: {e}"
    return text_results

# ==============================================================================
# 🧠 3. INTELIGÊNCIA (GEMINI - FORMATO PDF)
# ==============================================================================

def run_analysis(company, ticker, price_info):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=st.secrets["GOOGLE_API_KEY"],
        temperature=0.1
    )
    
    web_data = get_web_search_direct(f"{company} {ticker} ações notícias investidor histórico")

    # PROMPT ESTRUTURADO CONFORME PDF (Setor, Histórico, Produtos + Links)
    prompt = PromptTemplate.from_template(
        """
        Você é um analista sênior do portal 'Status Invest'.
        
        DADOS: {company} ({ticker}) | Preço: {price}
        NOTÍCIAS (Raw): {web_data}
        
        Gere um relatório MARKDOWN estritamente neste formato:
        
        ### 🏢 1. Perfil da Empresa
        * **Setor:** [Identifique o setor]
        * **Histórico:** [Resumo de 2-3 linhas sobre a fundação e origem]
        * **Produtos/Serviços:** [Liste os principais produtos]

        ### 📰 2. Destaques Recentes (Com Links)
        (Selecione 3 notícias dos dados. Use o formato de link Markdown OBRIGATÓRIO).
        
        * 🔗 **[TITULO_DA_NOTICIA](LINK_DA_NOTICIA)**
          *Fonte:* [Nome da Fonte]
          
        * 🔗 **[TITULO_DA_NOTICIA](LINK_DA_NOTICIA)**
          *Fonte:* [Nome da Fonte]

        ### 💡 3. Conclusão
        [Veredito de 1 linha sobre o momento da empresa]
        """
    )
    
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"company": company, "ticker": ticker, "price": price_info, "web_data": web_data})

# ==============================================================================
# 🖥️ 4. INTERFACE GRÁFICA (O DASHBOARD)
# ==============================================================================

def main():
    # --- HEADER ---
    st.markdown("## 📊 STATUS <span style='color:#FFB300'>INVEST</span> AI", unsafe_allow_html=True)
    
    # --- BARRA DE PESQUISA ---
    with st.container():
        st.markdown('<div class="invest-card" style="padding:10px;">', unsafe_allow_html=True)
        col_search, col_btn = st.columns([5, 1])
        with col_search:
            search_query = st.text_input("", placeholder="🔍 Busque por empresa ou ticker (ex: WEGE3, Petrobras)...", label_visibility="collapsed")
        with col_btn:
            search_btn = st.button("BUSCAR", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- LÓGICA DE EXIBIÇÃO ---
    
    # CASO 1: USUÁRIO PESQUISOU ALGO
    if search_btn and search_query:
        # 1. Identificar Ticker via Gemini (Rápido)
        llm_quick = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=st.secrets["GOOGLE_API_KEY"])
        ticker_finder = (PromptTemplate.from_template("Responda APENAS o ticker da ação {q} na B3 (ex: VALE3). Sem .SA") | llm_quick | StrOutputParser())
        ticker = ticker_finder.invoke({"q": search_query}).strip()
        
        # 2. Pegar Dados
        stock_data = get_stock_details(ticker)
        
        if stock_data:
            # HEADER DA AÇÃO
            cor_var = "#00C853" if stock_data['change'] >= 0 else "#D50000"
            st.markdown(f"""
            <div class="invest-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h1 style="margin:0;">{stock_data['ticker']}</h1>
                        <span style="color:gray;">{search_query.upper()}</span>
                    </div>
                    <div style="text-align:right;">
                        <h1 style="margin:0;">R$ {stock_data['price']:.2f}</h1>
                        <span style="color:{cor_var}; font-weight:bold; font-size:1.2em;">
                            {stock_data['change']:+.2f}%
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # RELATÓRIO GEMINI
            with st.spinner("Analisando fundamentos e notícias..."):
                report = run_analysis(search_query, ticker, stock_data['price'])
                st.markdown('<div class="invest-card">', unsafe_allow_html=True)
                st.markdown(report)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Ação não encontrada.")

    # CASO 2: TELA INICIAL (DASHBOARD ALTAS E BAIXAS)
    else:
        st.markdown("#### 📉 Visão de Mercado (Monitoramento IBOV)")
        altas, baixas = get_market_overview()
        
        col_altas, col_baixas = st.columns(2)
        
        # Renderizar Coluna de Altas
        with col_altas:
            st.markdown('<div class="invest-card"> <h4 style="border-bottom:2px solid #00C853; padding-bottom:10px;">🚀 Maiores Altas</h4>', unsafe_allow_html=True)
            if not altas.empty:
                for index, row in altas.iterrows():
                    st.markdown(f"""
                    <div class="stock-row">
                        <span class="ticker-badge">{row['Ticker']}</span>
                        <span class="price-val">R$ {row['Preço']:.2f}</span>
                        <span class="up-tag">▲ {row['Var']:.2f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write("Sem dados de alta no momento.")
            st.markdown('</div>', unsafe_allow_html=True)

        # Renderizar Coluna de Baixas
        with col_baixas:
            st.markdown('<div class="invest-card"> <h4 style="border-bottom:2px solid #D50000; padding-bottom:10px;">🔻 Maiores Baixas</h4>', unsafe_allow_html=True)
            if not baixas.empty:
                for index, row in baixas.iterrows():
                    st.markdown(f"""
                    <div class="stock-row">
                        <span class="ticker-badge">{row['Ticker']}</span>
                        <span class="price-val">R$ {row['Preço']:.2f}</span>
                        <span class="down-tag">▼ {row['Var']:.2f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write("Sem dados de baixa no momento.")
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()