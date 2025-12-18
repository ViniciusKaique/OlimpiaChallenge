import streamlit as st
import yfinance as yf
from duckduckgo_search import DDGS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==============================================================================
# 🎨 1. ESTILO VISUAL "STATUS INVEST" (CSS AVANÇADO)
# ==============================================================================
st.set_page_config(page_title="Status Invest AI", page_icon="📈", layout="wide")

# CSS para clonar o visual do site
st.markdown("""
<style>
    /* Fundo geral */
    .stApp {
        background-color: #F7F9FA;
        font-family: 'Barlow', sans-serif;
    }
    
    /* Remover barra superior padrão do Streamlit */
    header {visibility: hidden;}
    
    /* Cards brancos (Container) */
    .invest-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #E6E6E6;
        margin-bottom: 15px;
    }
    
    /* Títulos estilo Status Invest */
    h1, h2, h3 {
        color: #00294F !important;
        font-weight: 700;
    }
    
    /* Mini Card de Cotação (Altas/Baixas) */
    .mini-card {
        background: white;
        border-radius: 6px;
        padding: 15px;
        border-left: 5px solid #ddd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    .up { border-left-color: #00C853; }
    .down { border-left-color: #D50000; }
    
    .ticker-text { font-weight: bold; font-size: 1.1em; color: #333; }
    .price-text { font-size: 1.2em; font-weight: bold; color: #00294F; }
    .var-positive { color: #00C853; font-weight: bold; font-size: 0.9em; }
    .var-negative { color: #D50000; font-weight: bold; font-size: 0.9em; }

</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🛠️ 2. FERRAMENTAS DE DADOS (YFINANCE + DUCKDUCKGO)
# ==============================================================================

@st.cache_data(ttl=300)
def get_stock_data(ticker):
    """Pega dados financeiros reais."""
    if not ticker: return None
    clean = ticker.upper().strip()
    if not clean.endswith(".SA") and len(clean) <= 6: clean += ".SA"
    
    try:
        stock = yf.Ticker(clean)
        info = stock.fast_info
        price = info.last_price
        prev = info.previous_close
        
        if price and prev:
            change = ((price - prev) / prev) * 100
        else:
            change = 0.0
            
        return {"ticker": clean.replace(".SA",""), "price": price, "change": change}
    except:
        return None

def get_web_search_direct(query):
    """Busca manual para garantir que pegamos Título + Link (Exigência PDF)."""
    results_text = ""
    try:
        with DDGS() as ddgs:
            # Pega 4 resultados de notícias
            results = list(ddgs.news(query, region='br-pt', safesearch='off', max_results=4))
            for r in results:
                results_text += f"Titulo: {r['title']} | Link: {r['url']} | Fonte: {r['source']}\n"
    except Exception as e:
        results_text = f"Erro na busca: {str(e)}"
    return results_text

# ==============================================================================
# 🧠 3. INTELIGÊNCIA (PROMPT BASEADO NO PDF)
# ==============================================================================

def run_analysis(company, ticker, price_info):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=st.secrets["GOOGLE_API_KEY"],
        temperature=0.1
    )
    
    # Busca notícias específicas com o Ticker para ser preciso
    web_data = get_web_search_direct(f"{company} {ticker} investidor notícias financeiras recentes")

    # PROMPT RIGOROSO COM O PDF
    prompt = PromptTemplate.from_template(
        """
        Você é um analista financeiro do portal 'Status Invest'.
        
        EMPRESA: {company} ({ticker})
        PREÇO: {price}
        
        NOTÍCIAS (Raw Data):
        {web_data}
        
        ---
        Gere um relatório em MARKDOWN. Siga a estrutura abaixo e use os links fornecidos.
        
        ### 🏢 1. Perfil Corporativo
        (Responda em texto corrido, sem tópicos, cobrindo:)
        * **Setor:** Qual o setor de atuação?
        * **Histórico:** Breve resumo da origem.
        * **Produtos:** O que a empresa vende?
        
        ### 📰 2. Notícias & Comunicados
        (Selecione as 3 mais relevantes. Use o link original para tornar o título clicável).
        
        * 🔗 **[TITULO_DA_NOTICIA](LINK_DA_NOTICIA)**
          *Fonte:* [Nome da Fonte] - [Breve resumo de 1 linha]

        * 🔗 **[TITULO_DA_NOTICIA](LINK_DA_NOTICIA)**
          *Fonte:* [Nome da Fonte] - [Breve resumo de 1 linha]
          
        ### 💡 3. Conclusão
        [Veredito curto sobre o momento da empresa]
        """
    )
    
    chain = prompt | llm | StrOutputParser()
    
    return chain.invoke({
        "company": company,
        "ticker": ticker,
        "price": price_info,
        "web_data": web_data
    })

# ==============================================================================
# 🖥️ 4. INTERFACE GRÁFICA (O CLONE)
# ==============================================================================

def main():
    # --- HEADER / LOGO ---
    col_logo, col_empty = st.columns([1, 4])
    with col_