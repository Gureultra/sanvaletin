import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Ranking Gure Ultra",
    page_icon="🏆",
    layout="centered"
)

# 2. DISEÑO CSS PROFESIONAL
st.markdown("""
    <style>
    /* Fondo general oscuro suave */
    .stApp {
        background-color: #121212;
    }
    
    /* Tarjetas de información */
    div.stExpander, div.stAlert, .stTable {
        background-color: #1E1E1E !important;
        border: 1px solid #333 !important;
        border-radius: 12px !important;
        color: white !important;
    }

    /* Forzar textos en blanco para legibilidad */
    h1, h2, h3, p, label, .stMarkdown, .stTable td {
        color: #FFFFFF !important;
    }
    
    /* Subtítulos decorativos */
    .gray-text {
        color: #BBBBBB !important;
        font-size: 0.9rem;
        text-align: center;
    }

    /* Botones y acentos en rojo corporativo */
    .stButton>button {
        background-color: #FF4B4B !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        width: 100%;
    }

    /* Estilo para las métricas de puntos */
    [data-testid="stMetricValue"] {
        color: #FF4B4B !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CABECERA CON LOGO
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>Corazón de Hierro</h1>", unsafe_allow_html=True)
st.markdown("<p class='gray-text'>RETO DE INTENSIDAD Y RENDIMIENTO</p>", unsafe_allow_html=True)

# 4. INFORMACIÓN DEL RETO
st.write("")
with st.expander("📊 Ver sistema de puntuación"):
    st.markdown("""
    Los puntos se calculan automáticamente según el tiempo que pases en cada zona de pulso:
    - **Zona 1**: 1.0 pt/min  |  **Zona 2**: 1.5 pts/min
    - **Zona 3**: 3.0 pts/min |  **Zona 4**: 5.0 pts/min
    - **Zona 5**: 10.0 pts/min
    
    ❤️ **BONUS SAN VALENTÍN**: Actividades del 14 de febrero valen el **DOBLE (x2)**.
    """)

# 5. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Error al conectar con el Ranking. Verifica los Secrets.")
    st.stop()

# 6. PANEL DE SUBIDA
st.write("")
st.subheader("📤 Sube tu Entrenamiento")

# Usamos columnas para los inputs principales
c1, c2 = st.columns([1, 1])
with c1:
    nombre_usuario = st.text_input("Nombre o Nickname", placeholder="Ej: JUAN_PRO").strip().upper()
with c2:
    uploaded_file = st.file_uploader("Archivo .FIT", type=["fit"])

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Analizando datos de intensidad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Bonus San Valentín
            fecha_act = None
            for record in fitfile.get_messages('session'):
                fecha_act = record.get_value('start_time')
                if fecha_act: break
            es_sv = (fecha_act and fecha_act.month == 2 and fecha_act.day == 14)
            
            # Datos de pulso
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                z_limits = [114, 133, 152, 171, 220]
                mults = [1.0, 1.5, 3.0, 5.0, 10.0]
                puntos_total = 0
                stats = []
                factor = 2.0 if es_sv else 1.0

                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    p_zona = mins * mults[i] * factor
                    puntos_total += p_zona
                    if segs > 0:
                        stats.append({"Zona": f"Z{i+1}", "Tiempo": f"{int(mins)}m {int(segs%60)}s", "Puntos": round(p_zona, 2)})

                # --- MOSTRAR RESULTADOS ---
                st.write("")
                if es_sv: 
                    st.balloons()
                    st.success("🎯 ¡BONUS X2 APLICADO POR SAN VALENTÍN!")

                st.metric("PUNTOS SUMADOS", f"+ {round(puntos_total, 2)} pts")
                
                # Gráficas y tablas
                col_tab, col_graph = st.columns([1, 1])
                with col_tab:
                    st.markdown("**Desglose de Sesión**")
                    st.table(pd.DataFrame(stats))
                with col_graph:
                    st.markdown("**Frecuencia Cardíaca (BPM)**")
                    st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))

                # Actualizar base de datos
                df = conn.read(ttl=0)
                if df is None or df.empty:
                    df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0)
                
                if nombre_usuario in df['Ciclista'].values:
                    df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_total
                else:
                    new_row = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_total}])
                    df = pd.concat([df, new_row], ignore_index=True)
                
                conn.update(data=df)
                st.toast("Ranking actualizado correctamente")
            else:
                st.error("El archivo no contiene datos de ritmo cardíaco.")
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

# 7. RANKING GLOBAL
st.write("")
st.divider()
st.subheader("🏆 Clasificación General")

try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales'], errors='coerce')
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        # Añadir medalla al top 3
        ranking.index = ranking.index + 1
        st.dataframe(ranking, use_container_width=True)
    else:
        st.info("Todavía no hay actividades registradas este mes.")
except:
    st.info("Sincronizando clasificación...")
