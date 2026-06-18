import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import google.generativeai as genai
import PyPDF2
import pandas as pd  # IMPORTANTE: Adicionado!

# Configuração da IA
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("Consultor de Zoneamento")

lat = st.number_input("Latitude", format="%.6f")
lon = st.number_input("Longitude", format="%.6f")

if st.button("Gerar Parecer"):
    # 1. Carrega o mapa
    gdf = gpd.read_file("doc_67.kml")
    gdf = gdf.to_crs(epsg=4326)
    
    # IMPORTANTE: O Shapely usa Point(longitude, latitude)
    # Se você está digitando a Latitude primeiro no input, inverta aqui:
    ponto = Point(lon, lat) 
    
    # 2. Verifica em qual polígono o ponto está
    resultado = gdf[gdf.geometry.contains(ponto)]
    
    if not resultado.empty:
        # Pega o nome da zona (tenta coluna 'zona', se não, 'Name')
        nome_da_zona = resultado.iloc[0]['zona'] if 'zona' in resultado.columns and pd.notna(resultado.iloc[0]['zona']) else resultado.iloc[0]['Name']
        st.success(f"Imóvel localizado na: **{nome_da_zona}**")
        
        # 3. Leitura da lei
        leitor = PyPDF2.PdfReader("lei_67_OCR.pdf")
        texto_lei = "\n".join([p.extract_text() for p in leitor.pages])
        
        # 4. Geração do parecer
        prompt = f"O imóvel está na zona {nome_da_zona}. Baseado no texto da lei abaixo, gere um parecer técnico de viabilidade:\n\n{texto_lei[:15000]}"
        
        with st.spinner("Gerando parecer técnico..."):
            parecer = model.generate_content(prompt)
            st.markdown(parecer.text)
    else:
        st.error("Coordenada fora da área mapeada.")
        st.write("Dica: Verifique se a latitude e longitude não foram invertidas.")
        st.write("Limites do primeiro polígono do seu mapa:", gdf.geometry.iloc[0].bounds)
