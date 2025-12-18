import streamlit as st
import yfinance as yf
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import datetime

# ==============================================================================
# ⚙️ 1. CONFIGURAÇÃO E LISTA DE ATIVOS
# ==============================================================================
st.set_page_config(page_title="Finance AI Wrapper", page_icon="📈", layout="wide")

# Lista de ações líquidas para o "Top 5" (Para ser rápido, não baixamos o IBOV inteiro)
TOP_STOCKS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "WEGE3.SA", "ABEV3.SA",
    "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "RDOR3.SA", "B3SA3.SA", "EQTL3.SA",
    "PRIO3.SA", "RAIL3.SA", "GGBR4.SA", "JBSS3.SA", "VIVT3.SA", "CSAN3.SA", "ELET3.SA",
    "MGLU3.SA", "LREN3.SA", "AZUL4.SA", "GOLL4.SA", "HYPE3.SA"
]

# CSS para ficar parecido com Google Finance
st.markdown("""
<style>
    .big-font { font-size: 32px !important; font-weight: bold; }
    .metric-pos { color: #137333; font-weight: bold; }
    .metric-neg { color: #a50e0e; font-weight: bold; }
    .stButton button { border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🧠 2. INTELIGÊNCIA (LANGCHAIN)
# ==============================================================================
def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=st.secrets["GOOGLE_API_KEY"],
        temperature=0.0
    )

def identify_ticker_ai(query):
    """Transforma nome em Ticker usando IA"""
    llm = get_llm()
    template = """Retorne APENAS o código ticker da ação brasileira (.SA) para: {query}. Ex: 'Petrobras' -> 'PETR4.SA'. Sem texto extra."""
    chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
    try:
        return chain.invoke({"query": query}).strip()
    except:
        return None

def generate_summary_ai(ticker):
    """Gera resumo curto estilo Google"""
    llm = get_llm()
    template = """Para a empresa {ticker}, escreva um resumo de 3 linhas sobre o que ela faz e seu setor principal. Tom formal."""
    chain = PromptTemplate.from_template(template) | llm | StrOutputParser()
    return chain.invoke({"ticker": ticker})

# ==============================================================================
# 📊 3. DADOS DE MERCADO (YFINANCE)
# ==============================================================================

@st.cache_data(ttl=600)
def get_market_movers():
    """Calcula Top 5 Altas e Baixas da lista definida"""
    data = yf.download(TOP_STOCKS, period="2d", progress=False)['Close']
    
    # Calcula variação % do último dia
    changes = ((data.iloc[-1] - data.iloc[-2]) / data.iloc[-2]) * 100
    
    # Cria DataFrame e ordena
    df = pd.DataFrame({'Ticker': changes.index, 'Change': changes.values})
    df['Ticker'] = df['Ticker'].str.replace('.SA', '') # Limpa nome
    
    top_high = df.sort_values('Change', ascending=False).head(5)
    top_low = df.sort_values('Change', ascending=True).head(5)
    
    return top_high, top_low

def get_stock_details(ticker, period="1mo"):
    """Pega dados detalhados e histórico baseado no período selecionado"""
    stock = yf.Ticker(ticker)
    
    # Histórico dinâmico
    # Mapeamento: 1D (usamos 2d e intervalo curto), 5D, 1M, etc.
    interval = "1d"
    if period == "1d": 
        h = stock.history(period="1d", interval="15m") # Intraday
    elif period == "5d":
        h = stock.history(period="5d", interval="60m")
    else:
        h = stock.history(period=period) # Padrão diário

    info = stock.fast_info
    
    # Tenta pegar logo (às vezes o Yahoo tem, senão usamos placeholder)
    logo = stock.info.get('logo_url', 'https://cdn-icons-png.flaticon.com/512/7669/7669387.png')

    return {
        "price": info.last_price,
        "prev_close": info.previous_close,
        "history": h['Close'],
        "logo": logo,
        "name": ticker.replace('.SA', '')
    }

# ==============================================================================
# 🖥️ 4. INTERFACE DO USUÁRIO
# ==============================================================================

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2666/2666505.png", width=50)
    st.markdown("### Menu")
    mode = st.radio("Navegação", ["🏠 Início (Mercado)", "🔎 Pesquisar Ativo"])
    st.divider()
    st.caption("Powered by Gemini 1.5 & Yahoo Finance")

# --- PÁGINA INICIAL (TOP 5) ---
if mode == "🏠 Início (Mercado)":
    st.title("Resumo do Mercado")
    st.markdown("Monitoramento das principais ações do Brasil hoje.")
    
    with st.spinner("Atualizando ranking..."):
        highs, lows = get_market_movers()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚀 Maiores Altas")
        for _, row in highs.iterrows():
            st.markdown(f"**{row['Ticker']}**: <span style='color:green'>+{row['Change']:.2f}%</span>", unsafe_allow_html=True)
            st.progress(min(row['Change']/10, 1.0)) # Barra visual simples

    with col2:
        st.subheader("🔻 Maiores Baixas")
        for _, row in lows.iterrows():
            st.markdown(f"**{row['Ticker']}**: <span style='color:red'>{row['Change']:.2f}%</span>", unsafe_allow_html=True)
            st.progress(min(abs(row['Change'])/10, 1.0))

# --- PÁGINA DE PESQUISA (DETALHES) ---
elif mode == "🔎 Pesquisar Ativo":
    c_search, c_btn = st.columns([4, 1])
    with c_search:
        query = st.text_input("Busque uma empresa:", placeholder="Ex: Itaú, Vale, Magazine Luiza...")
    with c_btn:
        st.write("")
        st.write("")
        btn = st.button("Buscar", type="primary", use_container_width=True)

    if query:
        # 1. Identificar (LangChain)
        ticker = identify_ticker_ai(query)
        
        if ticker:
            # 2. Seletor de Tempo (Igual Google Finance)
            st.write("")
            time_cols = st.columns([1, 1, 1, 1, 1, 1, 6]) # Colunas para botões ficarem juntos
            
            # Controle de estado para o período
            period_map = {"1D": "1d", "5D": "5d", "1M": "1mo", "6M": "6mo", "1A": "1y", "Máx": "max"}
            selected_label = st.radio("Período", options=list(period_map.keys()), horizontal=True, label_visibility="collapsed")
            selected_period = period_map[selected_label]

            # 3. Baixar Dados
            try:
                data = get_stock_details(ticker, selected_period)
                
                # --- CABEÇALHO ESTILO GOOGLE ---
                st.divider()
                h_col1, h_col2 = st.columns([1, 5])
                
                with h_col1:
                    # Exibe Logo
                    st.image(data['logo'], width=80)
                
                with h_col2:
                    st.markdown(f"<div class='big-font'>{query.upper()} ({ticker})</div>", unsafe_allow_html=True)
                    
                    # Cálculo de variação
                    delta = data['price'] - data['prev_close']
                    delta_pct = (delta / data['prev_close']) * 100
                    color_cls = "metric-pos" if delta >= 0 else "metric-neg"
                    sinal = "+" if delta >= 0 else ""
                    
                    st.markdown(
                        f"""
                        <span style='font-size: 28px'>R$ {data['price']:.2f}</span> 
                        <span class='{color_cls}'> {sinal}{delta:.2f} ({sinal}{delta_pct:.2f}%) </span> hoje
                        """, 
                        unsafe_allow_html=True
                    )

                # --- GRÁFICO ---
                st.markdown("---")
                # Gráfico de linha simples e limpo
                st.line_chart(data['history'], color="#137333" if delta >= 0 else "#a50e0e", use_container_width=True)
                
                # --- RESUMO (LANGCHAIN) ---
                with st.expander("Sobre a empresa", expanded=True):
                    with st.spinner("Gerando resumo com IA..."):
                        summary = generate_summary_ai(ticker)
                        st.write("""Python file to serve as the frontend"""
import uuid

import streamlit as st
from streamlit_chat import message

from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver

def load_agent():
    """Logic for loading the agent you want to use should go here."""
    llm = init_chat_model("gpt-4o-mini", model_provider="openai", temperature=0)
    # You can declare tools here
    # https://python.langchain.com/docs/how_to/custom_tools/
    tools = []
    prompt = "Always respond like a pirate."
    checkpointer = MemorySaver()
    # https://langchain-ai.github.io/langgraph/reference/prebuilt/#langgraph.prebuilt.chat_agent_executor.create_react_agent
    graph = create_react_agent(
        llm,
        tools=tools,
        state_modifier=prompt,
        checkpointer=checkpointer
    )
    return graph

# From here down is all the StreamLit UI.
st.set_page_config(page_title="LangChain Demo", page_icon=":robot:")
st.header("LangChain Demo")

if "generated" not in st.session_state:
    st.session_state["generated"] = []

if "past" not in st.session_state:
    st.session_state["past"] = []

# Add thread_id and checkpointer initialization
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())

if "agent" not in st.session_state:
    st.session_state["agent"] = load_agent()

def get_text():
    input_text = st.text_input("You: ", "Hello, how are you?", key="input")
    return input_text


user_input = get_text()

if user_input:
    output = st.session_state["agent"].invoke({
        "messages": [{"role": "user", "content": user_input}]
    }, {
        "configurable": {"thread_id": st.session_state.thread_id}
    })

    st.session_state.past.append(user_input)
    # Final state in the messages are the output
    st.session_state.generated.append(output["messages"][-1].content)

if st.session_state["generated"]:

    for i in range(len(st.session_state["generated"]) - 1, -1, -1):
        message(st.session_state["generated"][i], key=str(i))
        message(st.session_state["past"][i], is_user=True, key=str(i) + "_user")summary)

            except Exception as e:
                st.error(f"Erro ao carregar dados: {e}")
        else:
            st.warning("Empresa não encontrada. Tente novamente.")