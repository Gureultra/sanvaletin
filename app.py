import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import base64

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Ranking Corazón de Hierro", layout="centered")

# ID del logo correcto extraído de tu enlace
LOGO_ID = "15ppJHj1Dsg06HBpv4eJnCgZMfhrDmqpX"
URL_LOGO = f"https://drive.google.com/thumbnail?id={LOGO_ID}&sz=w600"

# Mostrar logo centrado con un diseño limpio
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1 style='text-align: center;'>🏆 Ranking: Corazón de Hierro</h1>", unsafe_allow_html=True)

# 2. INFORMACIÓN DEL RETO
with st.expander("ℹ️ Ver baremo de puntos por zona"):
    st.write("""
    - **Z1**: 1 min = 1.0 punto
    - **Z2**: 1 min = 1.5 puntos
    - **Z3**: 1 min = 3.0 puntos
    - **Z4**: 1 min = 5.0 puntos
    - **Z5**: 1 min = 10.0 puntos
    """)
    st.info("❤️ **BONUS SAN VALENTÍN**: Las actividades del 14 de febrero valen el DOBLE.")

# 3. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# 4. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Nombre / Nickname:").strip().upper()
st.caption("⚠️ **Pon siempre el mismo nombre para sumar los puntos.**")

uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Detectar fecha (Bonus x2)
            fecha_act = None
            for record in fitfile.get_messages('session'):
                fecha_act = record.get_value('start_time')
                if fecha_act: break
            
            es_san_valentin = (fecha_act and fecha_act.month == 2 and fecha_act.day == 14)

            # Zonas de FC (Baremo estándar)
            z_limits = [114, 133, 152, 171, 220]

            # Extraer datos de pulso
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                mult_zonas = [1.0, 1.5, 3.0, 5.0, 10.0]
                stats_zonas = []
                puntos_act = 0
                bonus = 2.0 if es_san_valentin else 1.0

                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    pts = mins * mult_zonas[i] * bonus
                    puntos_act += pts
                    if segs > 0:
                        stats_zonas.append({"Zona": f"Z{i+1}", "Tiempo": f"{int(mins)}m {int(segs%60)}s", "Puntos": round(pts, 2)})

                if es_san_valentin:
                    st.balloons()
                    st.subheader("❤️ ¡PUNTOS DOBLES DE SAN VALENTÍN! ❤️")
                
                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_act, 2)} puntos!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Desglose de la sesión:**")
                    st.table(pd.DataFrame(stats_zonas))
                with col2:
                    st.write("**Esfuerzo (BPM):**")
                    st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))

                # ACTUALIZAR GOOGLE SHEETS
                df_ranking = conn.read(ttl=0)
                if df_ranking is None or df_ranking.empty:
                    df_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df_ranking['Puntos Totales'] = pd.to_numeric(df_ranking['Puntos Totales'], errors='coerce').fillna(0)

                if nombre_usuario in df_ranking['Ciclista'].values:
                    df_ranking.loc[df_ranking['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_act
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_act}])
                    df_ranking = pd.concat([df_ranking, nueva_fila], ignore_index=True)
                
                conn.update(data=df_ranking)
            else:
                st.error("No se encontraron datos de pulso.")
    except Exception as e:
        st.error(f"Error al procesar: {e}")

# 5. RANKING
st.divider()
st.subheader("📊 Ranking Mensual Acumulado")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales'], errors='coerce')
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False)
        st.dataframe(ranking, use_container_width=True, hide_index=True)
    else:
        st.info("Ranking vacío.")
except:
    st.info("Conectando con la base de datos...")
