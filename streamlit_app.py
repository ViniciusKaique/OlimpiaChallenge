import streamlit as st
import yfinance as yf
from langchain_google_genai import ChatGoogleGenerativeAI
from duckduckgo_search import DDGS # <--- MUDANÇA: Import direto da biblioteca
import time

# LangChain Core
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ==============================================================================
# BLOCO 1: CONFIGURAÇÃO
# ==============================================================================
st.set_page_config(page_title="Investment Banking AI", page_icon="📈", layout="wide")

# ==============================================================================
# BLOCO 2: FERRAMENTAS (TOOLS)
# ==============================================================================

@st.cache_data(ttl=600)
def get_stock_price(ticker_symbol):
    """Busca cotação com cache para evitar bloqueios."""
    if not ticker_symbol or ticker_symbol == "DESCONHECIDO":
        return "Ticker não identificado."
    
    clean_ticker = ticker_symbol.upper().strip()
    if not clean_ticker.endswith(".SA") and len(clean_ticker) <= 6:
        clean_ticker += ".SA"
        
    try:
        stock = yf.Ticker(clean_ticker)
        price = stock.fast_info.last_price
        if not price:
            history = stock.history(period="1d")
            if history.empty: return f"R$ 0.00 (Sem dados)"
            price = history['Close'].iloc[-1]
        return f"R$ {price:.2f}"
    except:
        return "Indisponível"

def get_web_search_direct(query):
    """
    Busca direta usando DDGS para garantir que pegamos os LINKS.
    Substitui a ferramenta do LangChain que estava dando erro.
    """
    results_text = ""
    try:
        # Busca 5 resultados trazendo corpo, título e LINK (href)
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region='br-pt', max_results=5))
            
            for result in results:
                # Montamos um texto estruturado para a IA ler
                results_text += f"""
                ---
                Título: {result['title']}
                Fonte/Link: {result['href']}
                Conteúdo: {result['body']}
                ---
                """
        return results_text
    except Exception as e:
        return f"Erro crítico na busca: {str(e)}"

# ==============================================================================
# BLOCO 3: SEGURANÇA
# ==============================================================================

def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if st.session_state["logged_in"]: return True

    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type="password")

    if st.sidebar.button("Entrar"):
        try:
            if (username == st.secrets["auth"]["username"] and 
                password == st.secrets["auth"]["password"]):
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.sidebar.error("Acesso Negado")
        except:
            st.error("Erro no secrets.toml")
    return False

# ==============================================================================
# BLOCO 4: LÓGICA (LANGCHAIN)
# ==============================================================================

def run_analysis(company_name):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", # Seu modelo atual
        google_api_key=st.secrets["GOOGLE_API_KEY"],
        temperature=0.1
    )

    # 1. Identificar Ticker
    ticker_prompt = PromptTemplate.from_template(
        "Identifique o código da ação (Ticker) da {company} na B3. Retorne APENAS o código (Ex: PETR4). Se não achar, retorne DESCONHECIDO."
    )
    ticker_chain = ticker_prompt | llm | StrOutputParser()
    
    with st.status("⚡ Analisando Mercado...", expanded=True) as status:
        st.write("🔍 Identificando Ticker...")
        ticker = ticker_chain.invoke({"company": company_name}).strip()
        
        st.write(f"💵 Buscando Cotação ({ticker})...")
        stock_price = get_stock_price(ticker)
        
        st.write("🌐 Buscando Notícias e Fontes (Isso garante os links)...")
        # Aqui usamos a nova função que corrige o erro e traz links
        search_query = f"{company_name} BVMF:{ticker} notícias mercado financeiro brasil"
        web_data = get_web_search_direct(search_query)
        
        status.update(label="Análise Pronta!", state="complete", expanded=False)

    # 2. Gerar Relatório
    final_prompt = PromptTemplate.from_template(
        """
        Você é um Analista Financeiro. Crie um relatório técnico.
        
        EMPRESA: {company} ({ticker}) | PREÇO: {stock_price}
        
        DADOS DA WEB (Com Links):
        {web_data}
        
        ---
        Gere o relatório em MARKDOWN seguindo ESTRITAMENTE este formato:
        
        ## 🏢 {company}
        **Ticker:** `{ticker}` | **Cotação:** {stock_price}
        
        ### 📊 Resumo Corporativo
        [Escreva um parágrafo denso sobre a empresa com base nos dados]
        
        ### 📰 Destaques e Fontes
        (Liste 3 notícias encontradas nos dados. É OBRIGATÓRIO incluir o Link/Fonte que veio nos dados da web).
        
        * **[Título da Notícia]**
          *Resumo:* [Resumo curto do fato]
          *🔗 Fonte:* [COPIE O LINK EXATO DOS DADOS AQUI]
        
        * **[Título da Notícia]**
          *Resumo:* [Resumo curto do fato]
          *🔗 Fonte:* [COPIE O LINK EXATO DOS DADOS AQUI]

        * **[Título da Notícia]**
          *Resumo:* [Resumo curto do fato]
          *🔗 Fonte:* [COPIE O LINK EXATO DOS DADOS AQUI]
        
        ### 💡 Conclusão
        [Veredito final curto]
        
        Data: 17/12/2025
        """
    )

    full_chain = final_prompt | llm | StrOutputParser()
    
    return full_chain.invoke({
        "company": company_name,
        "ticker": ticker,
        "stock_price": stock_price,
        "web_data": web_data
    })

# ==============================================================================
# BLOCO 5: INTERFACE
# ==============================================================================

def main():
    if not check_password(): st.stop()

    st.title("🏦 Investment Banking AI")
    st.caption("Relatórios com Fontes e Links Verificáveis")
    
    with st.form("main_form"):
        company = st.text_input("Nome da Empresa:", placeholder="Ex: Magazine Luiza")
        submitted = st.form_submit_button("Gerar Análise Completa")

    if submitted and company:
        try:
            result = run_analysis(company)
            st.markdown(result)
            st.download_button("📥 Baixar Relatório", result, file_name=f"{company}.md")
        except Exception as e:
            st.error(f"Erro: {e}")

if __name__ == "__main__":
    main()