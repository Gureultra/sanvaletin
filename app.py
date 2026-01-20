import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración de la página e Imagen
st.set_page_config(page_title="Ranking Reto Ciclista", layout="centered")

# Logotipo
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)

st.title("🏆 Ranking: Corazón de Hierro")
st.markdown("---")

# --- CONEXIÓN A GOOGLE SHEETS ---
# Configura la conexión usando tu URL específica
conn = st.connection("gsheets", type=GSheetsConnection)
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1kf6MwoAzD1vXmX_BfxRb0TVAZFf1-zZSzzuhe_HjstY/edit?usp=sharing"

# --- IDENTIFICACIÓN DEL CICLISTA ---
nombre_usuario = st.text_input(
    "Introduce tu nombre o nickname:", 
    help="⚠️ Usa siempre el mismo nombre para que tus puntos se sumen en el ranking mensual."
).strip().upper()

uploaded_file = st.file_uploader("Sube tu archivo .fit de la actividad", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    with st.spinner('Analizando tu esfuerzo...'):
        try:
            fitfile = fitparse.FitFile(uploaded_file)
            
            # 1. Intentar extraer zonas de frecuencia cardíaca del archivo
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            
            # Backup: Si el archivo no trae zonas, usamos una escala estándar (FC Max 190)
            if len(z_limits) < 4:
                z_limits = [114, 133, 152, 171, 220]
                st.info("ℹ️ No se detectaron zonas personalizadas en el archivo. Se han aplicado zonas estándar.")

            # 2. Procesar datos de pulso segundo a segundo
            hr_data = []
            for record in fitfile.get_messages('record'):
                hr = record.get_value('heart_rate')
                if hr: hr_data.append(hr)

            if hr_data:
                # Lógica de puntuación
                def calcular_puntos(hr):
                    if hr <= z_limits[0]: return 1.0 / 60   # Z1
                    if hr <= z_limits[1]: return 1.5 / 60   # Z2
                    if hr <= z_limits[2]: return 3.0 / 60   # Z3
                    if hr <= z_limits[3]: return 5.0 / 60   # Z4
                    return 10.0 / 60                        # Z5

                puntos_actividad = sum(calcular_puntos(hr) for hr in hr_data)

                # 3. Actualizar el ranking en Google Sheets
                # Leemos los datos actuales
                df_actual = conn.read(spreadsheet=spreadsheet_url)
                
                # Si la hoja está vacía o no tiene las columnas, las creamos
                if df_actual.empty or 'Nombre' not in df_actual.columns:
                    df_actual = pd.DataFrame(columns=['Nombre', 'Puntos'])

                if nombre_usuario in df_actual['Nombre'].values:
                    df_actual.loc[df_actual['Nombre'] == nombre_usuario, 'Puntos'] += puntos_actividad
                else:
                    nueva_fila = pd.DataFrame([{"Nombre": nombre_usuario, "Puntos": puntos_actividad}])
                    df_actual = pd.concat([df_actual, nueva_fila], ignore_index=True)
                
                # Guardar cambios
                conn.update(spreadsheet=spreadsheet_url, data=df_actual)
                st.success(f"✅ ¡Excelente, {nombre_usuario}! Has sumado {round(puntos_actividad, 2)} puntos al ranking.")
            else:
                st.error("❌ El archivo no contiene datos de frecuencia cardíaca.")
        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

# --- MOSTRAR EL RANKING ---
st.markdown("### 📊 Clasificación General")
try:
    # Leer el ranking actualizado
    ranking_final = conn.read(spreadsheet=spreadsheet_url, ttl="0")
    if not ranking_final.empty:
        ranking_final = ranking_final.sort_values(by="Puntos", ascending=False)
        # Mostrar tabla bonita
        st.dataframe(
            ranking_final, 
            use_container_width=True, 
            hide_index=True,
            column_config={"Puntos": st.column_config.NumberColumn(format="%.2f pts")}
        )
    else:
        st.write("Aún no hay datos. ¡Sube tu primera actividad!")
except Exception:
    st.info("Esperando la primera actividad para generar el ranking...")
