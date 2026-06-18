import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import zipfile
import tempfile
import os

# ==============================================================================
# CADASTRO DE DIRETRIZES URBANÍSTICAS (Lei Municipal de Aracati)
# ==============================================================================
DICIONARIO_ZONAS = {
    "ZPA": """
    ### 🌿 ZPA - Zona de Preservação Ambiental
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 0  |
    | **Taxa de Permeabilidade (T.P)** | 100%  |
    """,

    "ZOC": """
    ### 🏘️ ZOC - Zona de Ocupação Controlada
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 0,5  |
    | **Taxa de Permeabilidade (T.P)** | 60%  |
    | **Recuo Frontal** | 3,00m  |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa)  |
    | **Área Mínima do Lote** | 300m²  |
    | **Testada Mínima** | 8,00m  |
    
    *Nota: Para templos religiosos, a T.P mínima é de 15%.*
    """,

    "ZUS": """
    ### 🌾 ZUS - Zona de Uso Sustentável
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Parâmetros Gerais** | Os índices devem seguir estritamente a Legislação Específica da Unidade de Conservação. |
    """,

    "ZDU 1": """
    ### 🏙️ ZDU 1 - Zona de Desenvolvimento Urbano 1
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,5  |
    | **Taxa de Permeabilidade (T.P)** | 30%  |
    | **Recuo Frontal** | Suficiente para liberar calçada de 4,00m (vias locais) ou 5,00m (vias do Sist. Viário Básico)  |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa)  |
    | **Área Mínima do Lote** | 150m²  |
    | **Testada Mínima** | 8,00m |
    """,

    "ZDU 2": """
    ### 🏙️ ZDU 2 - Zona de Desenvolvimento Urbano 2
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,5  |
    | **Taxa de Permeabilidade (T.P)** | 30% |
    | **Recuo Frontal** | 3,00m  |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa) |
    | **Área Mínima do Lote** | 175m² (Lotes menores que 200m² consolidados antes desta lei são aceitos com certidão)  |
    | **Testada Mínima** | 6,00m  |
    """,

    "ZEU": """
    ### 📈 ZEU - Zona de Expansão Urbana
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,0 |
    | **Taxa de Permeabilidade (T.P)** | 30% |
    | **Recuo Frontal** | 3,00m |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa)  |
    | **Área Mínima do Lote** | 200m²  |
    | **Testada Mínima** | 7,00m  |
    """,

    "ZT 1": """
    ### 🔄 ZT 1 - Zona de Transição 1
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,5  |
    | **Taxa de Permeabilidade (T.P)** | 30% |
    | **Recuo Frontal** | 3,00m  |
    | **Gabarito Máximo** | 10,00m (Pode ser elevado até 13m na laje ou 15m no topo com Outorga Onerosa) |
    | **Área Mínima do Lote** | 150m²  |
    | **Testada Mínima** | 8,00m  |
    """,

    "ZT 2": """
    ### 🔄 ZT 2 - Zona de Transição 2
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 0,5 |
    | **Taxa de Permeabilidade (T.P)** | 50%  |
    | **Recuo Frontal** | 3,00m |
    | **Gabarito Máximo** | 8,50m  |
    | **Área Mínima do Lote** | 200m²  |
    | **Testada Mínima** | 6,00m  |
    """,

    "Zona Especial de Desenvolvimento Econômico e Turístico": """
    ### 🏖️ ZEDET - Zona Especial de Desenvolvimento Econômico e Turístico
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 1,5  |
    | **Taxa de Permeabilidade (T.P)** | 30% |
    | **Recuo Frontal** | Suficiente para liberar calçada de 4,00m (vias locais) ou 5,00m (vias do Sist. Viário Básico) |
    | **Gabarito Máximo** | Elevável para 10m (laje) ou 12m (topo) com Outorga Onerosa. Em Majorlândia, base é 10m podendo ir a 13m/15m. |
    | **Área Mínima do Lote** | 125m²  |
    | **Testada Mínima** | 8,00m |
    
    *Nota: Em Canoa Quebrada e Beirada, prevalecem os parâmetros de lei específica da APA.*
    """,

    "ZEIC": """
    ### 🏛️ ZEIC - Zona Especial de Interesse Cultural
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Testada Mínima** | 8,00m |
    | **Demais Índices** | Conforme Seção II do Cap IV da lei e portarias específicas. |
    """,

    "ZEA": """
    ### ✈️ ZEA - Zona Especial Aeroportuária
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Testada Mínima** | 6,00m  |
    | **Demais Índices** | Conforme regulação específica do COMAR ou os mesmos da ZEU na ausência desta. |
    """,

    "ZEIS": """
    ### 🤝 ZEIS - Zona Especial de Interesse Social
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Gabarito Máximo** | 10,00m (Podendo chegar a 13m na laje/15m topo com Outorga Onerosa) |
    | **Testada Mínima** | 5,00m |
    | **Demais Índices** | Definidos no Projeto de Regularização (ou opção pela zona lindeira se não houver projeto). |
    
    *Nota: Podem ser suprimidos área mínima e testada se promovido pelo poder público.*
    """,

    "Zona Industrial": """
    ### 🏭 ZI - Zona Industrial
    | Parâmetro Urbanístico | Índice Permitido |
    | :--- | :--- |
    | **Índice de Aproveitamento Básico** | 2,0  |
    | **Taxa de Permeabilidade (T.P)** | 30%  |
    | **Gabarito Máximo** | 10,00m |
    | **Testada Mínima** | 8,00m |
    """
}

# ==============================================================================
# INTERFACE DO STREAMLIT
# ==============================================================================
st.title("📍 Consultor de Zoneamento Automático")
st.write("Insira as coordenadas para descobrir os índices urbanísticos instantaneamente.")

# Coordenadas padrão
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
            # ==========================================
            # MODO DEBUG: Vê todas as zonas que se sobrepõem
            # ==========================================
            todas_as_zonas = resultado['zona'].dropna().unique().tolist()
            
            st.info(f"🔍 **Detalhe de Sobreposição:** Esta coordenada intercepta {len(todas_as_zonas)} polígono(s): {todas_as_zonas}")
            
            # Se tocar em mais de uma, tenta ignorar a "Zona Rural" para dar preferência à zona urbana específica
            if len(todas_as_zonas) > 1 and "Zona Rural" in todas_as_zonas:
                todas_as_zonas.remove("Zona Rural")
                
            # Seleciona a zona final (a mais específica)
            nome_da_zona = todas_as_zonas[0]
            # ==========================================

            st.success(f"📍 Imóvel localizado na: **{nome_da_zona}**")
            
            st.write("---")
            
            # Busca os índices no dicionário local
            dados_urbanisticos = DICIONARIO_ZONAS.get(nome_da_zona, f"⚠️ Os parâmetros para a **{nome_da_zona}** ainda não foram cadastrados.")
            
            # Exibe a tabela na tela
            st.markdown(dados_urbanisticos)
            
            # ==========================================
            # GERAÇÃO DO PARECER PARA DOWNLOAD
            # ==========================================
            st.write("---")
            st.subheader("🖨️ Exportar Resultado")
            
            texto_parecer = f"""==================================================
        PARECER TÉCNICO DE ZONEAMENTO
==================================================

DADOS DA CONSULTA:
- Latitude: {lat}
- Longitude: {lon}
- Zoneamento Identificado: {nome_da_zona}

{dados_urbanisticos}

==================================================
Documento gerado automaticamente pelo sistema de 
Consulta de Zoneamento Municipal.
=================================================="""
            
            st.download_button(
                label="📄 Baixar Parecer Técnico (.txt)",
                data=texto_parecer,
                file_name=f"Parecer_Zoneamento_{nome_da_zona.replace(' ', '_')}.txt",
                mime="text/plain"
            )
            
        else:
            st.error("Coordenada fora da área mapeada.")

    except Exception as e:
        st.error(f"Erro ao processar o mapa: {e}")
