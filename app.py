import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Ranking Gure Ultra",
    page_icon="❤️",
    layout="centered"
)

# Estilos CSS mejorados
st.markdown("""
    <style>
    /* Fondo de la web al 70% negro aprox (#1A1A1A) */
    .stApp {
        background-color: #1A1A1A;
    }

    /* Forzar que todos los textos base sean blancos */
    .stMarkdown, p, li, label, span {
        color: #FFFFFF !important;
    }

    /* Títulos en rojo */
    h1, h2, h3 {
        color: #FF4B4B !important;
        text-align: center;
    }

    /* --- ARREGLO PARA CAJAS DE TEXTO --- */
    /* Aseguramos que el texto dentro de los inputs sea NEGRO o muy oscuro 
       si el fondo es blanco, o BLANCO si el fondo es oscuro */
    input {
        color: #31333F !important; /* Color estándar de texto para inputs de Streamlit */
    }
    
    /* Si el usuario tiene el tema oscuro del navegador, esto asegura legibilidad */
    div[data-baseweb="input"] {
        border-radius: 8px;
    }

    /* Estilo para las tablas */
    .stTable {
        background-color: #262730;
        border-radius: 10px;
    }
    
    /* Ajuste de márgenes del logo */
    .stImage > img {
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. LOGOTIPO Y CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"

col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #BBBBBB; margin-top: -15px;'>Reto de Intensidad Gure Ultra</p>", unsafe_allow_html=True)

# 3. INFORMACIÓN DEL RETO
with st.expander("ℹ️ Ver Baremo de Puntos y Bonus"):
    st.markdown("""
    **Puntos por tiempo en zona:**
    * **Zona 1**: 1.0 pt/min
    * **Zona 2**: 1.5 pts/min
    * **Zona 3**: 3.0 pts/min
    * **Zona 4**: 5.0 pts/min
    * **Zona 5**: 10.0 pts/min
    """)
    st.info("❤️ **BONUS**: Actividades del 14 de febrero valen el DOBLE.")

# 4. CONEXIÓN
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.stop()

# 5. CARGA DE ACTIVIDAD
st.divider()
st.subheader("📤 Sube tu actividad")

nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()
uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Procesando...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Fecha para Bonus
            fecha_act = None
            for record in fitfile.get_messages('session'):
                fecha_act = record.get_value('start_time')
                if fecha_act: break
            
            es_san_valentin = (fecha_act and fecha_act.month == 2 and fecha_act.day == 14)
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                z_limits = [114, 133, 152, 171, 220]
                mult_zonas = [1.0, 1.5, 3.0, 5.0, 10.0]
                puntos_act = 0
                stats_zonas = []
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

                if es_san_valentin: st.balloons()
                st.markdown(f"### ✅ ¡Has sumado **{round(puntos_act, 2)}** puntos!")
                
                c1, c2 = st.columns(2)
                with c1: st.table(pd.DataFrame(stats_zonas))
                with c2: st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))

                # Guardar datos
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
                st.toast("Ranking actualizado.")
    except Exception as e:
        st.error(f"Error: {e}")

# 6. RANKING
st.divider()
st.subheader("📊 Ranking General")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales'], errors='coerce')
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False)
        st.dataframe(ranking, use_container_width=True, hide_index=True)
except:
    pass
