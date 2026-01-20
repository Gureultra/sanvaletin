import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración e Imagen
st.set_page_config(page_title="Ranking Ciclista", layout="centered")
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)

st.title("🏆 Ranking: Corazón de Hierro")

# Conexión a Google Sheets para el ranking persistente
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. Identificación
nombre_usuario = st.text_input(
    "Tu Nombre:", 
    help="Usa siempre el mismo para acumular tus puntos."
).strip().upper()

uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    with st.spinner('Leyendo zonas y datos del archivo...'):
        fitfile = fitparse.FitFile(uploaded_file)
        
        # Extraer zonas del archivo (si están disponibles)
        z_limits = []
        for record in fitfile.get_messages('hr_zone'):
            data = record.get_values()
            if 'high_value' in data:
                z_limits.append(data['high_value'])
        
        # Si no hay zonas en el fit, usamos un backup estándar
        if len(z_limits) < 4:
            z_limits = [114, 133, 152, 171, 200]
        
        # Procesar frecuencia cardíaca
        hr_data = []
        for record in fitfile.get_messages('record'):
            hr = record.get_value('heart_rate')
            if hr: hr_data.append(hr)

        if hr_data:
            df = pd.DataFrame(hr_data, columns=['hr'])
            
            # Multiplicadores según tu regla
            def calcular_puntos(hr):
                if hr <= z_limits[0]: return 1.0   # Z1
                if hr <= z_limits[1]: return 1.5   # Z2
                if hr <= z_limits[2]: return 3.0   # Z3
                if hr <= z_limits[3]: return 5.0   # Z4
                return 10.0                        # Z5

            df['puntos_seg'] = df['hr'].apply(lambda x: calcular_puntos(x) / 60)
            puntos_totales = df['puntos_seg'].sum()

            # ACTUALIZAR GOOGLE SHEETS
            existing_data = conn.read()
            if nombre_usuario in existing_data['Nombre'].values:
                existing_data.loc[existing_data['Nombre'] == nombre_usuario, 'Puntos'] += puntos_totales
            else:
                new_row = pd.DataFrame([{"Nombre": nombre_usuario, "Puntos": puntos_totales}])
                existing_data = pd.concat([existing_data, new_row], ignore_index=True)
            
            conn.update(data=existing_data)
            st.success(f"✅ ¡{round(puntos_totales, 2)} puntos sumados a tu cuenta!")

# --- MOSTRAR RANKING ---
st.divider()
st.subheader("📊 Clasificación General")
try:
    df_ranking = conn.read().sort_values(by="Puntos", ascending=False)
    st.dataframe(df_ranking, use_container_width=True, hide_index=True)
except:
    st.info("Sube la primera actividad para inaugurar el ranking.")
