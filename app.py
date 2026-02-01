import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Gure Ultra | Ranking Corazón de Hierro",
    page_icon="🔥",
    layout="centered"
)

# 2. DISEÑO PROFESIONAL (Fondo 70% negro y legibilidad de letras)
st.markdown("""
    <style>
    /* Fondo principal: Negro al 70% (#1A1A1A) */
    .stApp {
        background-color: #1A1A1A;
    }
    
    /* Forzar visibilidad de textos en blanco puro */
    h1, h2, h3, p, label, .stMarkdown, li, span {
        color: #FFFFFF !important;
    }
    
    /* Títulos en rojo corporativo */
    h1, h2, h3 {
        color: #FF4B4B !important;
        text-align: center;
    }

    /* Estilo para las cajas de entrada (Inputs) */
    div[data-baseweb="input"] {
        background-color: #2D2D2D !important;
        border: 1px solid #444 !important;
        border-radius: 8px !important;
    }

    /* Texto dentro de los campos de entrada - NEGRO para que se lea en cajas blancas */
    input {
        color: #31333F !important;
    }

    /* Cuadro de advertencia personalizado */
    .warning-box {
        background-color: #332200;
        border-left: 5px solid #FFA500;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        color: #FFFFFF !important;
    }

    /* Tablas legibles */
    .stTable {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CABECERA Y LOGO
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #BBBBBB;'>RETO DE INTENSIDAD GURE ULTRA</p>", unsafe_allow_html=True)

# 4. ADVERTENCIA DE IDENTIDAD
st.markdown("""
    <div class="warning-box">
        <span style="color: #FFA500; font-weight: bold;">⚠️ AVISO IMPORTANTE:</span><br>
        Para que tus puntos se sumen correctamente, usa siempre <b>EL MISMO NOMBRE O NICKNAME</b> en cada actividad que subas.
    </div>
    """, unsafe_allow_html=True)

# 5. INFORMACIÓN DEL RETO
with st.expander("ℹ️ Ver Baremo de Puntos y Bonus"):
    st.markdown("""
    Los puntos se calculan automáticamente según el tiempo en tus zonas de pulso:
    - **Zona 1**: 1.0 pt/min  |  **Zona 2**: 1.5 pts/min
    - **Zona 3**: 3.0 pts/min |  **Zona 4**: 5.0 pts/min
    - **Zona 5**: 10.0 pts/min
    
    ❤️ **BONUS SAN VALENTÍN**: ¡Las actividades del 14 de febrero valen el **DOBLE**!
    """)

# 6. PANEL DE SUBIDA
st.divider()
st.subheader("📤 Sube tu actividad")
nombre_usuario = st.text_input("Tu Nombre / Nickname:", placeholder="Ejemplo: JUAN_PEREZ")
uploaded_file = st.file_uploader("Selecciona tu archivo .FIT de tu reloj", type=["fit"])

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Analizando datos...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Obtener fecha de la actividad
            fecha_act = None
            for record in fitfile.get_messages('session'):
                fecha_act_raw = record.get_value('start_time')
                if fecha_act_raw:
                    fecha_act = fecha_act_raw.date()
                    break
            
            # --- VALIDACIÓN DE FECHA ---
            inicio_reto = date(2026, 2, 1)
            fin_reto = date(2026, 3, 1)

            if not fecha_act or not (inicio_reto <= fecha_act <= fin_reto):
                st.error(f"❌ Fecha de actividad no válida: {fecha_act if fecha_act else 'Desconocida'}")
                st.warning("Solo se permiten actividades realizadas entre el 1 de febrero y el 1 de marzo de 2026.")
                st.stop()

            # Procesamiento de pulso
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                z_limits = [114, 133, 152, 171, 220]
                mults = [1.0, 1.5, 3.0, 5.0, 10.0]
                puntos_total = 0
                stats = []
                es_sv = (fecha_act.month == 2 and fecha_act.day == 14)
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

                # MOSTRAR RESULTADOS
                if es_sv: st.balloons()
                st.metric("PUNTOS SUMADOS", f"+ {round(puntos_total, 2)}")
                
                c_tab, c_graph = st.columns([1, 1.2])
                with c_tab:
                    st.table(pd.DataFrame(stats))
                with c_graph:
                    st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))

                # ACTUALIZAR GOOGLE SHEETS
                conn = st.connection("gsheets", type=GSheetsConnection)
                df = conn.read(ttl=0)
                if df is None or df.empty:
                    df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0)
                nombre_clean = nombre_usuario.strip().upper()
                
                if nombre_clean in df['Ciclista'].values:
                    df.loc[df['Ciclista'] == nombre_clean, 'Puntos Totales'] += puntos_total
                else:
                    new_row = pd.DataFrame([{'Ciclista': nombre_clean, 'Puntos Totales': puntos_total}])
                    df = pd.concat([df, new_row], ignore_index=True)
                
                conn.update(data=df)
                st.toast(f"¡Hecho! Puntos guardados para {nombre_clean}")
            else:
                st.error("No se detectó frecuencia cardíaca en el archivo.")
    except Exception as e:
        st.error("Error al procesar el archivo.")

# 7. CLASIFICACIÓN
st.divider()
st.subheader("🏆 Clasificación General")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales'], errors='coerce')
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1
        st.dataframe(ranking, use_container_width=True)
except:
    st.info("Sincronizando...")
