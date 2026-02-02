import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import altair as alt

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Gure Ultra | Ranking Corazón de Hierro",
    page_icon="🔥",
    layout="centered"
)

# 2. DISEÑO CSS EXTREMO (Fondo oscuro, letras blancas e inputs legibles)
st.markdown("""
    <style>
    .stApp {
        background-color: #1A1A1A !important;
    }
    
    /* Forzar texto blanco en toda la interfaz */
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3 {
        color: #FFFFFF !important;
    }
    
    h1, h2, h3 {
        color: #FF4B4B !important;
        text-align: center;
        font-weight: bold;
    }

    /* Estilo de la tabla de ranking */
    .stDataFrame, .stTable {
        background-color: #2D2D2D !important;
        color: white !important;
    }

    /* Caja de texto del nombre: Texto NEGRO sobre fondo BLANCO para que se lea al escribir */
    input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #FF4B4B !important;
        font-weight: bold;
    }

    /* --- CAJA DE SUBIDA (ROJO Y ESPAÑOL) --- */
    [data-testid="stFileUploader"] {
        background-color: #262730 !important;
        border: 2px dashed #FF0000 !important;
        border-radius: 15px !important;
    }
    
    [data-testid="stFileUploader"] section div span {
        font-size: 0 !important;
    }
    [data-testid="stFileUploader"] section div span::before {
        content: "Arrastra tu archivo .FIT aquí";
        color: #FF0000 !important;
        font-size: 16px !important;
        font-weight: bold;
    }
    [data-testid="stFileUploader"] button span::before {
        content: "Buscar archivo";
        color: #FF0000 !important;
        font-size: 14px !important;
    }

    .warning-box {
        background-color: #332200 !important;
        border-left: 5px solid #FFA500 !important;
        padding: 15px !important;
        border-radius: 8px !important;
        margin-bottom: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Error de conexión.")

# 4. CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"
st.image(URL_LOGO, width=250)
st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. INSTRUCCIONES
st.markdown("""
    <div class="warning-box">
        <b>📋 REGLAS DEL RETO:</b><br>
        • Usa siempre <b>EL MISMO NOMBRE</b> para acumular tus puntos.<br>
        • Periodo: <b>1 de febrero al 1 de marzo de 2026</b>.<br>
        • ❤️ <b>SAN VALENTÍN (14 Feb):</b> ¡Puntúa <b>DOBLE (x2)</b>!<br>
        • <b>Zonas:</b> Z5, Z6 y Z7 valen 10 pts/min.
    </div>
    """, unsafe_allow_html=True)

# 6. PANEL DE ENTRADA
st.divider()
nombre_usuario = st.text_input("Escribe tu nombre EXACTO aquí:").strip().upper()
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file and nombre_usuario:
    try:
        fitfile = fitparse.FitFile(uploaded_file)
        fecha_act = None
        for record in fitfile.get_messages('session'):
            if record.get_value('start_time'):
                fecha_act = record.get_value('start_time').date()
                break
        
        # Validar fechas
        if not fecha_act or not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
            st.error(f"❌ Fecha {fecha_act} no permitida.")
            st.stop()

        # Procesar FC
        hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]
        if hr_records:
            z_limits = [114, 133, 152, 171] 
            mults = [1.0, 1.5, 3.0, 5.0, 10.0]
            es_sv = (fecha_act.month == 2 and fecha_act.day == 14)
            factor = 2.0 if es_sv else 1.0
            puntos_sesion = 0
            desglose = []

            for i in range(4):
                if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                p_z = (segs/60) * mults[i] * factor
                puntos_sesion += p_z
                if segs > 0: desglose.append({"Zona": f"Z{i+1}", "Pts": round(p_z, 2)})

            segs_max = sum(1 for hr in hr_records if hr > z_limits[3])
            if segs_max > 0:
                p_max = (segs_max/60) * mults[4] * factor
                puntos_sesion += p_max
                desglose.append({"Zona": "Z5/6/7", "Pts": round(p_max, 2)})

            # Guardar
            df = conn.read(ttl=0)
            if df is None or df.empty: df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
            df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)
            if nombre_usuario in df['Ciclista'].values:
                df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_sesion
            else:
                new_row = pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [puntos_sesion]})
                df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=df)
            
            st.success(f"✅ ¡Puntos guardados! +{round(puntos_sesion, 2)}")
            st.table(pd.DataFrame(desglose))
    except:
        st.error("Error al leer el archivo.")

# 7. RANKING Y GRÁFICA (FORZANDO COLORES BLANCOS)
st.divider()
st.subheader("🏆 Clasificación General")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales']).round(2)
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        
        st.dataframe(ranking, use_container_width=True)

        st.write("")
        st.subheader("📊 Gráfica de Rendimiento")
        
        # GRÁFICA ALTAIR CON CONFIGURACIÓN DE COLOR BLANCO
        chart = alt.Chart(ranking).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Puntos Totales:Q', title='Puntos Totales', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', title='Ciclista', axis=alt.Axis(labelColor='white', titleColor='white')),
            tooltip=['Ciclista', 'Puntos Totales']
        ).properties(
            height=alt.Step(40),
            background='transparent'
        ).configure_view(
            strokeOpacity=0
        ).configure_axis(
            grid=False,
            domainColor='white',
            tickColor='white'
        ).configure_legend(
            labelColor='white',
            titleColor='white'
        )
        
        st.altair_chart(chart, use_container_width=True)
except:
    st.info("Cargando datos...")
