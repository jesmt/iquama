import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import google.generativeai as genai
import PyPDF2
import pandas as pd

# Configuração da IA
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("Consultor de Zoneamento")

lat = st.number_input("Latitude", format="%.6f", value=-4.504)
lon = st.number_input("Longitude", format="%.6f", value=-37.782)

if st.button("Gerar Parecer"):
    try:
        # 1. Carrega e diagnostica o mapa
        gdf = gpd.read_file("doc_67.kml")
        gdf = gdf.to_crs(epsg=4326)
        
        # Ponto (Longitude, Latitude)
        ponto = Point(lon, lat)
        
        # Filtra a zona
        resultado = gdf[gdf.geometry.contains(ponto)]
        
        if not resultado.empty:
            # Identifica o nome da zona
            nome_da_zona = resultado.iloc[0]['zona'] if 'zona' in resultado.columns and pd.notna(resultado.iloc[0]['zona']) else resultado.iloc[0]['Name']
            st.success(f"Imóvel localizado na: **{nome_da_zona}**")
            
            # 2. Leitura da lei com verificação de segurança
            with open("lei_67_OCR.pdf", "rb") as f:
                leitor = PyPDF2.PdfReader(f)
                texto_lei = "\n".join([p.extract_text() for p in leitor.pages if p.extract_text()])
            
            if len(texto_lei) < 100:
                st.warning("Atenção: O PDF parece estar vazio ou ser apenas imagens. Tente um PDF com texto selecionável.")
            
            # 3. Geração do parecer
            prompt = f"Você é um técnico de urbanismo. O imóvel está na zona {nome_da_zona}. Baseado no texto da lei fornecido, gere um parecer técnico sobre os índices permitidos:\n\n{texto_lei[:15000]}"
            
            with st.spinner("Gerando parecer técnico..."):
                parecer = model.generate_content(prompt)
                st.markdown(parecer.text)
                
        else:
            st.error("Coordenada fora da área mapeada.")
            st.write("---")
            st.write("DEBUG - Informações do mapa:")
            st.write(f"Total de polígonos no mapa: {len(gdf)}")
            st.write("Limites (bbox) do primeiro polígono:", gdf.geometry.iloc[0].bounds)
            st.write("Verifique se sua coordenada está dentro desses limites.")
            
    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")
        st.write("Dica: Verifique se os arquivos 'doc_67.kml' e 'lei_67_OCR.pdf' estão na pasta raiz do repositório.")
