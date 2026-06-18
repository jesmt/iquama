'''import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import google.generativeai as genai
import PyPDF2
import pandas as pd
import zipfile
import tempfile
import os

# Configuração da IA com Fallback de Segurança
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    model = genai.GenerativeModel('gemini-pro')

st.title("Consultor de Zoneamento")

# Coordenadas padrão da Matriz de Aracati
lat = st.number_input("Latitude", format="%.6f", value=-4.5606)
lon = st.number_input("Longitude", format="%.6f", value=-37.7712)

if st.button("Gerar Parecer"):
    try:
        # 1. Descompacta o KMZ para um KML temporário direto no servidor
        with zipfile.ZipFile("zoneamento_67.kmz", "r") as z:
            kml_interno = [f for f in z.namelist() if f.endswith('.kml')][0]
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_file:
                tmp_file.write(z.read(kml_interno))
                tmp_path = tmp_file.name

        # 2. Descobre TODAS as camadas (pastas de zonas) dentro do arquivo
        layer_names = []
        try:
            import pyogrio
            info = pyogrio.list_layers(tmp_path)
            layer_names = info[:, 0].tolist() if not isinstance(info, tuple) else list(info[0])
        except Exception:
            try:
                import fiona
                layer_names = fiona.listlayers(tmp_path)
            except Exception:
                pass

        # 3. Varre camada por camada e unifica tudo em um grande mapa
        gdfs = []
        if layer_names:
            for layer in layer_names:
                try:
                    sub_gdf = gpd.read_file(tmp_path, layer=layer)
                    
                    # Garante que cada polígono saiba a qual zona pertence (usa o nome da pasta se necessário)
                    if 'zona' not in sub_gdf.columns:
                        if 'Name' in sub_gdf.columns:
                            sub_gdf['zona'] = sub_gdf['Name'].apply(lambda x: x if pd.notna(x) and str(x).strip() != "" else layer)
                        else:
                            sub_gdf['zona'] = layer
                    gdfs.append(sub_gdf)
                except Exception:
                    continue
            
            if gdfs:
                gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)
            else:
                gdf = gpd.read_file(tmp_path)
        else:
            gdf = gpd.read_file(tmp_path)
        
        # Converte o mapa unificado para coordenadas geográficas globais
        gdf = gdf.to_crs(epsg=4326)
        
        # Remove o arquivo temporário com segurança
        os.unlink(tmp_path)
        
        # Cria o ponto geográfico para teste (Longitude, Latitude)
        ponto = Point(lon, lat)
        
        # Filtra a zona que contém a coordenada informada
        resultado = gdf[gdf.geometry.contains(ponto)]
        
        if not resultado.empty:
            nome_da_zona = resultado.iloc[0].get('zona', resultado.iloc[0].get('Name', 'Zona Indefinida'))
            st.success(f"Imóvel localizado na: **{nome_da_zona}**")
            
            # 4. Leitura do arquivo de texto da Lei de Zoneamento
            with open("lei_67_OCR.pdf", "rb") as f:
                leitor = PyPDF2.PdfReader(f)
                texto_lei = "\n".join([p.extract_text() for p in leitor.pages if p.extract_text()])
            
            if len(texto_lei) < 100:
                st.warning("Atenção: O PDF parece não conter camadas de texto reconhecíveis.")
            
            # 5. Geração do parecer analítico com a IA
            prompt = f"Você é um engenheiro/técnico de urbanismo. O imóvel avaliado está localizado na {nome_da_zona}. Baseado estritamente no texto da lei fornecido a seguir, gere um parecer técnico detalhado contendo os índices urbanísticos permitidos (recuos, taxa de ocupação, gabarito, etc.):\n\n{texto_lei[:15000]}"
            
            with st.spinner("Analisando parâmetros urbanísticos com a IA..."):
                parecer = model.generate_content(prompt)
                st.markdown(parecer.text)
                
        else:
            st.error("Coordenada fora da área mapeada.")
            st.write("---")
            st.write("DEBUG - Informações do mapa unificado:")
            st.write(f"Total de polígonos combinados de todas as zonas: {len(gdf)}")
            st.write("Zonas/Camadas lidas com sucesso:", layer_names)
            
    except Exception as e:
        st.error(f"Ocorreu um erro no processamento: {e}")'''





import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import zipfile
import tempfile
import os

# ==============================================================================
# CADASTRO DE DIRETRIZES (Substitua pelos dados reais da lei do seu município)
# O nome aqui deve ser IGUAL ao nome que aparece no KMZ da prefeitura
# ==============================================================================
# ==============================================================================
# CADASTRO DE DIRETRIZES URBANÍSTICAS (Lei Municipal de Aracati)
# As chaves do dicionário devem corresponder ao nome que o seu KMZ exibe.
# ==============================================================================
DICIONARIO_ZONAS = {
    "ZPA": """
    ### 🌿 ZPA - Zona de Preservação Ambiental
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 0 [cite: 3] |
    | **Taxa de Permeabilidade (T.P)** | 100% [cite: 3] |
    """,

    "ZOC": """
    ### 🏘️ ZOC - Zona de Ocupação Controlada
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 0,5 [cite: 3] |
    | **Taxa de Permeabilidade (T.P)** | 60% [cite: 3] |
    | **Recuo Frontal** | 3,00m [cite: 3] |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa) [cite: 3, 18, 19] |
    | **Área Mínima do Lote** | 300m² [cite: 3] |
    | **Testada Mínima** | 8,00m [cite: 3] |
    
    *Nota: Para templos religiosos, a T.P mínima é de 15%[cite: 27].*
    """,

    "ZUS": """
    ### 🌾 ZUS - Zona de Uso Sustentável
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Parâmetros Gerais** | Os índices devem seguir estritamente a Legislação Específica da Unidade de Conservação[cite: 3, 13]. |
    """,

    "ZDU 1": """
    ### 🏙️ ZDU 1 - Zona de Desenvolvimento Urbano 1
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,5 [cite: 3] |
    | **Taxa de Permeabilidade (T.P)** | 30% [cite: 3] |
    | **Recuo Frontal** | Suficiente para liberar calçada de 4,00m (vias locais) ou 5,00m (vias do Sist. Viário Básico) [cite: 3, 10] |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa) [cite: 3, 18, 19] |
    | **Área Mínima do Lote** | 150m² [cite: 3] |
    | **Testada Mínima** | 8,00m [cite: 3] |
    """,

    "ZDU 2": """
    ### 🏙️ ZDU 2 - Zona de Desenvolvimento Urbano 2
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,5 [cite: 3] |
    | **Taxa de Permeabilidade (T.P)** | 30% [cite: 3] |
    | **Recuo Frontal** | 3,00m [cite: 3] |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa) [cite: 3, 18, 19] |
    | **Área Mínima do Lote** | 175m² (Lotes menores que 200m² consolidados antes desta lei são aceitos com certidão) [cite: 3, 20] |
    | **Testada Mínima** | 6,00m [cite: 3] |
    """,

    "ZEU": """
    ### 📈 ZEU - Zona de Expansão Urbana
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,0 [cite: 3] |
    | **Taxa de Permeabilidade (T.P)** | 30% [cite: 3] |
    | **Recuo Frontal** | 3,00m [cite: 3] |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa) [cite: 3, 18, 19] |
    | **Área Mínima do Lote** | 200m² [cite: 3] |
    | **Testada Mínima** | 7,00m [cite: 3] |
    """,

    "ZT 1": """
    ### 🔄 ZT 1 - Zona de Transição 1
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,5 [cite: 3] |
    | **Taxa de Permeabilidade (T.P)** | 30% [cite: 3] |
    | **Recuo Frontal** | 3,00m [cite: 3] |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa) [cite: 3, 18, 19] |
    | **Área Mínima do Lote** | 150m² [cite: 3] |
    | **Testada Mínima** | 8,00m [cite: 3] |
    """,

    "ZT 2": """
    ### 🔄 ZT 2 - Zona de Transição 2
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 0,5 [cite: 3] |
    | **Taxa de Permeabilidade (T.P)** | 50% [cite: 3] |
    | **Recuo Frontal** | 3,00m [cite: 3] |
    | **Gabarito Máximo** | 8,50m [cite: 3, 18] |
    | **Área Mínima do Lote** | 200m² [cite: 3] |
    | **Testada Mínima** | 6,00m [cite: 3] |
    """,

    "ZEDET": """
    ### 🏖️ ZEDET - Zona Especial de Desenvolvimento Econômico e Turístico
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,5 [cite: 3] |
    | **Taxa de Permeabilidade (T.P)** | 30% [cite: 3] |
    | **Recuo Frontal** | Suficiente para liberar calçada de 4,00m (vias locais) ou 5,00m (vias do Sist. Viário Básico) [cite: 3, 10] |
    | **Gabarito Máximo** | Elevável para 10m (laje) ou 12m (topo) com Outorga Onerosa[cite: 3, 25]. Em Majorlândia, base é 10m podendo ir a 13m/15m[cite: 26]. |
    | **Área Mínima do Lote** | 125m² [cite: 3] |
    | **Testada Mínima** | 8,00m [cite: 3] |
    
    *Nota: Em Canoa Quebrada e Beirada, prevalecem os parâmetros de lei específica da APA[cite: 3, 17].*
    """,

    "ZEIC": """
    ### 🏛️ ZEIC - Zona Especial de Interesse Cultural
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Testada Mínima** | 8,00m [cite: 8] |
    | **Demais Índices** | Conforme Seção II do Cap IV da lei e portarias específicas[cite: 8, 14]. |
    """,

    "ZEA": """
    ### ✈️ ZEA - Zona Especial Aeroportuária
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Testada Mínima** | 6,00m [cite: 8] |
    | **Demais Índices** | Conforme regulação específica do COMAR ou os mesmos da ZEU na ausência desta[cite: 8, 15]. |
    """,

    "ZEIS": """
    ### 🤝 ZEIS - Zona Especial de Interesse Social
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Gabarito Máximo** | 10,00m (Podendo chegar a 13m na laje/15m topo com Outorga Onerosa) [cite: 8, 18, 19] |
    | **Testada Mínima** | 5,00m [cite: 8] |
    | **Demais Índices** | Definidos no Projeto de Regularização (ou opção pela zona lindeira se não houver projeto)[cite: 8, 16]. |
    
    *Nota: Podem ser suprimidos área mínima e testada se promovido pelo poder público[cite: 24].*
    """,

    "ZI": """
    ### 🏭 ZI - Zona Industrial
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 2,0 [cite: 8] |
    | **Taxa de Permeabilidade (T.P)** | 30% [cite: 8] |
    | **Gabarito Máximo** | 10,00m [cite: 8, 18] |
    | **Testada Mínima** | 8,00m [cite: 8] |
    """
}

# ==============================================================================
# INTERFACE DO STREAMLIT
# ==============================================================================
st.title("📍 Consultor de Zoneamento Automático")
st.write("Insira as coordenadas para descobrir os índices urbanísticos instantaneamente.")

# Coordenadas padrão (Ex: Matriz de Aracati)
lat = st.number_input("Latitude", format="%.6f", value=-4.5606)
lon = st.number_input("Longitude", format="%.6f", value=-37.7712)

if st.button("Consultar Índices"):
    try:
        # 1. Descompacta o KMZ na memória do servidor
        with zipfile.ZipFile("zoneamento_67.kmz", "r") as z:
            kml_interno = [f for f in z.namelist() if f.endswith('.kml')][0]
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp_file:
                tmp_file.write(z.read(kml_interno))
                tmp_path = tmp_file.name

        # 2. Descobre e lê todas as camadas do KMZ
        layer_names = []
        try:
            import pyogrio
            info = pyogrio.list_layers(tmp_path)
            layer_names = info[:, 0].tolist() if not isinstance(info, tuple) else list(info[0])
        except Exception:
            try:
                import fiona
                layer_names = fiona.listlayers(tmp_path)
            except Exception:
                pass

        gdfs = []
        if layer_names:
            for layer in layer_names:
                try:
                    sub_gdf = gpd.read_file(tmp_path, layer=layer)
                    if 'zona' not in sub_gdf.columns:
                        if 'Name' in sub_gdf.columns:
                            sub_gdf['zona'] = sub_gdf['Name'].apply(lambda x: x if pd.notna(x) and str(x).strip() != "" else layer)
                        else:
                            sub_gdf['zona'] = layer
                    gdfs.append(sub_gdf)
                except Exception:
                    continue
            gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs) if gdfs else gpd.read_file(tmp_path)
        else:
            gdf = gpd.read_file(tmp_path)
        
        gdf = gdf.to_crs(epsg=4326)
        os.unlink(tmp_path)  # Limpa o arquivo temporário
        
        # 3. Executa a busca espacial
        ponto = Point(lon, lat)
        resultado = gdf[gdf.geometry.contains(ponto)]
        
        if not resultado.empty:
            nome_da_zona = resultado.iloc[0].get('zona', resultado.iloc[0].get('Name', 'Zona Indefinida'))
            st.success(f"📍 Imóvel localizado na: **{nome_da_zona}**")
            
            st.write("---")
            # 4. Busca os índices no dicionário local
            # Se o nome exato da zona não estiver cadastrado no dicionário, avisa o usuário
            dados_urbanisticos = DICIONARIO_ZONAS.get(nome_da_zona, f"⚠️ Os parâmetros para a **{nome_da_zona}** ainda não foram cadastrados no código.")
            
            # Exibe a tabela formatada na tela
            st.markdown(dados_urbanisticos)
                
        else:
            st.error("Coordenada fora da área mapeada.")
            st.write("---")
            st.write(f"DEBUG: O mapa possui {len(gdf)} polígonos divididos em: {layer_names}")
            
    except Exception as e:
        st.error(f"Erro ao processamento o mapa: {e}")
