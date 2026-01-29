import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Gure Ultra | Ranking Corazón de Hierro",
    page_icon="🔥",
    layout="centered"
)

# 2. ESTILOS CSS PARA UN DISEÑO MODERNO
st.markdown("""
    <style>
    /* Fondo oscuro profesional */
    .stApp {
        background-color: #0E1117;
    }
    
    /* Forzar visibilidad de textos */
    h1, h2, h3, p, label, .stMarkdown, .stTable td {
        color: #FFFFFF !important;
    }
    
    /* Advertencia resaltada */
    .warning-box {
        background-color: #2E1A05;
        border-left: 5px solid #FFA500;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }

    /* Tarjetas de resultados */
    .result-card {
        background-color: #1E2128;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363D;
        margin-top: 15px;
    }

    /* Estilo para los inputs */
    div[data-baseweb="input"] {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
    }
    
    /* Botón de Streamlit */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>Corazón de Hierro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8B949E;'>RETO DE INTENSIDAD GURE ULTRA</p>", unsafe_allow_html=True)

# 4. ADVERTENCIA IMPORTANTE (NOMBRE DE USUARIO)
st.markdown(f"""
    <div class="warning-box">
        <span style="color: #FFA500; font-weight: bold;">⚠️ AVISO IMPORTANTE:</span><br>
        Para que tus puntos se acumulen correctamente en el ranking, debes usar <b>EXACTAMENTE EL MISMO NOMBRE</b> cada vez que subas una actividad.
    </div>
    """, unsafe_allow_html=True)

# 5. INFORMACIÓN DEL RETO
with st.expander("📊 Ver sistema de puntuación"):
    st.markdown("""
    Puntos por minuto según tu frecuencia cardíaca:
    - **Zona 1**: 1.0 pt/min  |  **Zona 2**: 1.5 pts/min
    - **Zona 3**: 3.0 pts/min |  **Zona 4**: 5.0 pts/min
    - **Zona 5**: 10.0 pts/min
    
    ❤️ **BONUS SAN VALENTÍN**: Las actividades del 14 de febrero valen el **DOBLE (x2)**.
    """)

# 6. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Error al conectar con el Ranking.")
    st.stop()

# 7. PANEL DE SUBIDA
st.markdown("### 📤 Sube tu Entrenamiento")
c1, c2 = st.columns([1, 1])
with c1:
    nombre_usuario = st.text_input("Tu Nombre / Nickname", placeholder="Ej: MIGUEL_84").strip().upper()
with c2:
    uploaded_file = st.file_uploader("Archivo .FIT", type=["fit"])

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Analizando datos...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Lógica de Bonus
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
                        stats.append({"Zona": f"Z{i+1}", "Tiempo": f"{int(mins)}m {int(segs%60)}s", "Pts": round(p_zona, 1)})

                # --- MOSTRAR RESULTADOS ---
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                if es_sv: 
                    st.balloons()
                    st.success("🎯 ¡BONUS SAN VALENTÍN ACTIVADO (x2)!")
                
                st.metric("PUNTOS GANADOS", f"+ {round(puntos_total, 2)}")
                
                col_tab, col_graph = st.columns([1, 1.2])
                with col_tab:
                    st.markdown("**Desglose por Zona**")
                    st.dataframe(pd.DataFrame(stats), hide_index=True)
                with col_graph:
                    st.markdown("**Ritmo Cardíaco**")
                    st.line_chart(pd.DataFrame(hr_records, columns=['BPM']), height=150)
                st.markdown('</div>', unsafe_allow_html=True)

                # --- GUARDAR EN RANKING ---
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
                st.toast(f"¡Hecho! Puntos sumados a {nombre_usuario}")
            else:
                st.error("No se detectaron datos de frecuencia cardíaca.")
    except Exception as e:
        st.error(f"Error al leer el archivo FIT.")

# 8. RANKING GLOBAL
st.write("")
st.divider()
st.subheader("🏆 Clasificación Gure Ultra")

try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales'], errors='coerce')
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1 # Ranking 1, 2, 3...
        st.table(ranking)
    else:
        st.info("El ranking está esperando al primer valiente. ¡Sube tu FIT!")
except:
    st.info("Actualizando clasificación...")
