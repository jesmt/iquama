import streamlit as st
import google.generativeai as genai
import os

# 1. Configuração da página do Chatbot
st.set_page_config(page_title="Assitente IQUAMA", page_icon="🤖")
st.title("🤖 Assistente Virtual - Leis do IQUAMA")
st.caption("Tire suas dúvidas sobre o Controle Urbanístico e Ambiental de Aracati.")

# 2. Configurar a chave da API do Gemini (Pegando das variáveis seguras do servidor)
# Na hospedagem gratuita, você colocará sua chave com o nome GEMINI_API_KEY
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Por favor, configure a chave GEMINI_API_KEY nos Secrets.")
    st.stop()

# 3. Carregar o arquivo de leis na memória do Gemini (Apenas uma vez)
@st.cache_resource
def carregar_leis():
    # Certifique-se de que o arquivo 'LeisIQUAMA.pdf' está na mesma pasta do código
    caminho_pdf = "LeisIQUAMA.pdf" 
    if os.path.exists(caminho_pdf):
        with st.spinner("Carregando base jurídica..."):
            # Envia o arquivo nativamente para a API do Gemini
            arquivo_gemini = genai.upload_file(caminho_pdf)
            return arquivo_gemini
    else:
        st.error("Arquivo LeisIQUAMA.pdf não encontrado no servidor.")
        st.stop()

arquivo_leis = carregar_leis()

# Instruction (O comando que obriga ele a ser preciso e citar artigos/anexos)
PROMPT_SISTEMA = """
Você é um assistente virtual oficial e gratuito para ajudar os cidadãos a tirarem dúvidas sobre as Leis de Controle Urbanístico e Ambiental (IQUAMA) de Aracati.
Você responderá perguntas estritamente baseado no arquivo PDF anexado.

Regras Cruciais:
1. Seja extremamente preciso. Se a resposta estiver em uma tabela ou anexo, cite detalhadamente (Ex: "O valor é 300 UFIRM, conforme o Item 10 do Anexo III da Lei...").
2. Sempre cite o Artigo, Parágrafo ou Anexo de onde retirou a informação.
3. Se a informação NÃO estiver no PDF, diga textualmente: "Desculpe, não encontrei essa informação específica na legislação disponível. Recomendo consultar diretamente o órgão do IQUAMA." Não invente nada.
"""

# 4. Inicializar o histórico da conversa na tela
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensagens anteriores
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
            
            # Enviamos o PDF INTEIRO + a pergunta do usuário
            response = model.generate_content([arquivo_leis, prompt])
            
            texto_resposta = response.text
            message_placeholder.markdown(texto_resposta)
            st.session_state.messages.append({"role": "assistant", "content": texto_resposta})
            
        except Exception as e:
            st.error(f"Erro ao processar: {e}")