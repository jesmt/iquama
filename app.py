import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import google.generativeai as genai
import PyPDF2

# Configuração da IA (Use o 'Secrets' do Streamlit para não expor a chave)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("Consultor de Zoneamento")

# Upload dos arquivos (caso não queira deixar fixo no repo)
lat = st.number_input("Latitude", format="%.6f")
lon = st.number_input("Longitude", format="%.6f")

if st.button("Gerar Parecer"):
    # Carrega o mapa
    gdf = gpd.read_file("doc_67.kml")
    gdf = gdf.to_crs(epsg=4326) # Isso força o mapa a "entender" latitude e longitude
    ponto = Point(lon, lat)
    
    # Busca a zona
    resultado = gdf[gdf.contains(ponto)]
    
    if not resultado.empty:
        zona = resultado.iloc[0]['Name']
        st.success(f"Zona encontrada: {zona}")
        
        # Leitura da lei
        leitor = PyPDF2.PdfReader("lei_67_OCR.pdf")
        texto_lei = "\n".join([p.extract_text() for p in leitor.pages])
        
        prompt = f"O imóvel está na zona {zona}. Baseado no texto da lei abaixo, gere um parecer técnico de viabilidade:\n\n{texto_lei[:15000]}"
        
        parecer = model.generate_content(prompt)
        st.write(parecer.text)
    else:
        st.error("Coordenada fora da área mapeada.")
