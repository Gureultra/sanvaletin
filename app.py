import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA Y TEMA OSCURO
st.set_page_config(
    page_title="Ranking Gure Ultra | Corazón de Hierro",
    page_icon="🏆",
    layout="centered"
)

# Estilos CSS para forzar un diseño oscuro y elegante
st.markdown("""
    <style>
    .main {
        background-color: #121212;
        color: #ffffff;
    }
    .stTextInput > div > div > input {
        background-color: #262730;
        color: white;
    }
    .stTable {
        background-color: #262730;
        border-radius: 10px;
    }
    h1, h2, h3 {
        color: #FF4B4B !important;
    }
    .stMetric {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. LOGOTIPO Y TÍTULO
# Usamos la URL directa proporcionada para el nuevo logo
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1 style='text-align: center;'>Corazón de Hierro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Reto de Intensidad Gure Ultra</p>", unsafe_allow_html=True)

# 3. INFORMACIÓN DEL RETO (Expandible oscuro)
with st.expander("ℹ️ Ver Baremo de Puntos y Bonus"):
    st.markdown("""
    - **Zona 1**: 1.0 pt/min
    - **Zona 2**: 1.5 pts/min
    - **Zona 3**: 3.0 pts/min
    - **Zona 4**: 5.0 pts/min
    - **Zona 5**: 10.0 pts/min
    """)
    st.info("❤️ **BONUS SAN VALENTÍN**: Actividades realizadas el 14 de febrero suman el **DOBLE de puntos**.")

# 4. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

# 5. ENTRADA DE USUARIO
with st.container():
    st.subheader("📤 Sube tu actividad")
    nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()
    uploaded_file = st.file_uploader("Archivo .fit de tu reloj", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Procesando datos de frecuencia cardíaca...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Detectar fecha para Bonus San Valentín
            fecha_act = None
            for record in fitfile.get_messages('session'):
                fecha_act = record.get_value('start_time')
                if fecha_act: break
            
            es_san_valentin = (fecha_act and fecha_act.month == 2 and fecha_act.day == 14)

            # Extraer registros de pulso
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                # Baremo estándar (se ajusta según zonas de usuario si el FIT las trae, si no, estándar)
                z_limits = [114, 133, 152, 171, 220]
                mult_zonas = [1.0, 1.5, 3.0, 5.0, 10.0]
                stats_zonas = []
                puntos_act = 0
                factor_bonus = 2.0 if es_san_valentin else 1.0

                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    pts = mins * mult_zonas[i] * factor_bonus
                    puntos_act += pts
                    if segs > 0:
                        stats_zonas.append({
                            "Zona": f"Z{i+1}", 
                            "Tiempo": f"{int(mins)}m {int(segs%60)}s", 
                            "Puntos": round(pts, 2)
                        })

                # Mostrar resultados
                if es_san_valentin:
                    st.balloons()
                    st.success("🎯 **¡BONUS APLICADO!** Puntos x2 por San Valentín.")
                
                st.metric(label="Puntos Sumados", value=f"{round(puntos_act, 2)} pts")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Desglose por zonas:**")
                    st.table(pd.DataFrame(stats_zonas))
                with c2:
                    st.write("**Gráfica de Pulsaciones:**")
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
                st.error("El archivo no contiene datos de frecuencia cardíaca.")
    except Exception as e:
        st.error(f"Error al analizar el archivo FIT: {e}")

# 6. RANKING GLOBAL (Sección inferior)
st.divider()
st.subheader("📊 Clasificación General")
try:
    ranking_final = conn.read(ttl=0)
    if ranking_final is not None and not ranking_final.empty:
        ranking_final['Puntos Totales'] = pd.to_numeric(ranking_final['Puntos Totales'], errors='coerce')
        ranking_final = ranking_final.sort_values(by='Puntos Totales', ascending=False)
        st.dataframe(ranking_final, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay registros. ¡Sube el primer entrenamiento!")
except:
    st.info("Cargando ranking...")
