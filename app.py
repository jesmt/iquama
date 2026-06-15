import streamlit as st
import google.generativeai as genai
import os
import pypdf

# 1. Configuração da página do Chatbot
st.set_page_config(page_title="Assistente IQUAMA", page_icon="🤖")
st.title("🤖 Assistente Virtual - Leis do IQUAMA")
st.caption("Tire suas dúvidas sobre o Controle Urbanístico e Ambiental de Aracati.")

# 2. Configurar a chave da API do Gemini
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Por favor, configure a chave GEMINI_API_KEY nos Secrets do Streamlit.")
    st.stop()

# 3. Extrair o texto do PDF localmente (Bypassa o limite de 4MB da API)
@st.cache_data
def extrair_texto_pdf():
    caminho_pdf = "LeisIQUAMA.pdf" 
    if os.path.exists(caminho_pdf):
        with st.spinner("Carregando e processando a base jurídica (isso ocorre apenas uma vez)..."):
            reader = pypdf.PdfReader(caminho_pdf)
            texto_completo = ""
            for pagina in reader.pages:
                texto_completo += pagina.extract_text() + "\n"
            return texto_completo
    else:
        st.error("Arquivo LeisIQUAMA.pdf não encontrado no servidor do GitHub.")
        st.stop()

texto_leis = extrair_texto_pdf()

# Instruções com o texto das leis injetado diretamente no cérebro do bot
PROMPT_SISTEMA = f"""
Você é um assistente virtual oficial e gratuito para ajudar os cidadãos a tirarem dúvidas sobre as Leis de Controle Urbanístico e Ambiental (IQUAMA) de Aracati.

Regras Cruciais:
1. Seja extremamente preciso. Se a resposta estiver em uma tabela ou anexo, cite detalhadamente (Ex: "O valor é de 300 UFIRM, conforme o Item 10 do Anexo III da Lei Complementar nº 017/2019").
2. Sempre cite o Artigo, Parágrafo, Item ou Anexo de onde retirou a informação para dar segurança jurídica ao cidadão.
3. Você deve responder perguntas baseando-se estritamente no texto das leis fornecido abaixo.
4. Se a informação NÃO estiver no texto abaixo, diga textualmente: "Desculpe, não encontrei essa informação específica na legislação disponível. Recomendo consultar diretamente o órgão do IQUAMA." Não invente nenhum dado ou valor.

---
TEXTO OFICIAL DAS LEIS DO IQUAMA:
{texto_leis}
---
"""

# 4. Inicializar o histórico da conversa na tela
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensagens anteriores na tela
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Onde o cidadão digita a pergunta
if prompt := st.chat_input("Ex: Qual o valor da consulta prévia?"):
    # Mostra a pergunta do cidadão
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gera a resposta usando o Gemini 1.5 Flash
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=PROMPT_SISTEMA
            )
            
            # Enviamos apenas a pergunta, pois a lei já está salva na memória do modelo
            response = model.generate_content(prompt)
            
            texto_resposta = response.text
            message_placeholder.markdown(texto_resposta)
            st.session_state.messages.append({"role": "assistant", "content": texto_resposta})
            
        except Exception as e:
            st.error(f"Erro ao processar a resposta da IA: {e}")
