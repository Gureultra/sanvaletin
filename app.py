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

# 2. DISEÑO CSS "ULTRA" (Fondo 70% negro, textos blancos, caja roja/español)
st.markdown("""
    <style>
    .stApp { background-color: #1A1A1A !important; }
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3 {
        color: #FFFFFF !important;
    }
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; font-weight: bold; }
    
    /* Input del nombre: Fondo blanco, letras NEGRAS para leer bien al escribir */
    input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #FF4B4B !important;
        font-weight: bold;
    }

    /* Caja de subida personalizada */
    [data-testid="stFileUploader"] {
        background-color: #262730 !important;
        border: 2px dashed #FF0000 !important;
        border-radius: 15px;
    }
    [data-testid="stFileUploader"] section div span { font-size: 0 !important; }
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
    st.error("Error de conexión con la base de datos.")

# 4. CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"
st.image(URL_LOGO, width=250)
st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

st.markdown("""
    <div class="warning-box">
        <b>📋 PUNTUACIÓN POR ZONA (pt/min):</b><br>
        • Z1: 1 | Z2: 1.5 | Z3: 3 | Z4: 5 | <b>Z5, Z6 y Z7: 10 pts</b>.<br>
        • ❤️ <b>14 DE FEBRERO:</b> ¡PUNTUACIÓN DOBLE!<br>
        • Usa siempre el mismo nombre para acumular tus puntos.
    </div>
    """, unsafe_allow_html=True)

# 5. PANEL DE ENTRADA
nombre_usuario = st.text_input("Escribe tu nombre exactamente igual que siempre:").strip().upper()
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file and nombre_usuario:
    try:
        fitfile = fitparse.FitFile(uploaded_file)
        
        # Extraer fecha
        fecha_act = None
        for record in fitfile.get_messages('session'):
            st_time = record.get_value('start_time')
            if st_time:
                fecha_act = st_time.date()
                break
        
        if not fecha_act or not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
            st.error(f"❌ Archivo con fecha {fecha_act}. Fuera de rango (Feb 2026).")
            st.stop()

        # Extraer registros de pulso
        hr_data = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate') is not None]
        
        if hr_data:
            # Definición de Límites BPM (Z1 a Z7)
            # Ejemplo estándar: Z1(<114), Z2(114-133), Z3(133-152), Z4(152-171), Z5(171-185), Z6(185-195), Z7(>195)
            z_limits = [114, 133, 152, 171, 185, 195] 
            
            # Baremo de puntos
            mults = { 
                "Z1": 1.0, "Z2": 1.5, "Z3": 3.0, "Z4": 5.0, 
                "Z5": 10.0, "Z6": 10.0, "Z7": 10.0 
            }
            
            es_sv = (fecha_act.month == 2 and fecha_act.day == 14)
            bonus = 2.0 if es_sv else 1.0
            
            # Conteo de segundos por zona
            sec_z1 = sum(1 for hr in hr_data if hr <= z_limits[0])
            sec_z2 = sum(1 for hr in hr_data if z_limits[0] < hr <= z_limits[1])
            sec_z3 = sum(1 for hr in hr_data if z_limits[1] < hr <= z_limits[2])
            sec_z4 = sum(1 for hr in hr_data if z_limits[2] < hr <= z_limits[3])
            sec_z5 = sum(1 for hr in hr_data if z_limits[3] < hr <= z_limits[4])
            sec_z6 = sum(1 for hr in hr_data if z_limits[4] < hr <= z_limits[5])
            sec_z7 = sum(1 for hr in hr_data if hr > z_limits[5])

            zonas_calculo = [
                ("Zona 1", sec_z1, mults["Z1"]),
                ("Zona 2", sec_z2, mults["Z2"]),
                ("Zona 3", sec_z3, mults["Z3"]),
                ("Zona 4", sec_z4, mults["Z4"]),
                ("Zona 5", sec_z5, mults["Z5"]),
                ("Zona 6", sec_z6, mults["Z6"]),
                ("Zona 7", sec_z7, mults["Z7"])
            ]

            puntos_sesion = 0
            tabla_resumen = []

            for nombre, segs, m in zonas_calculo:
                if segs > 0:
                    mins_frac = segs / 60
                    p_zona = mins_frac * m * bonus
                    puntos_sesion += p_zona
                    tabla_resumen.append({
                        "Zona": nombre,
                        "Tiempo": f"{int(segs // 60)} min {int(segs % 60)} seg",
                        "Puntos": round(p_zona, 2)
                    })

            # Actualizar Ranking en GSheets
            df = conn.read(ttl=0)
            if df is None or df.empty:
                df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
            
            df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)

            if nombre_usuario in df['Ciclista'].values:
                df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_sesion
            else:
                new_row = pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [puntos_sesion]})
                df = pd.concat([df, new_row], ignore_index=True)
            
            conn.update(data=df)

            # Feedback visual
            if es_sv: st.balloons(); st.markdown("### ❤️ ¡BONUS SAN VALENTÍN x2 APLICADO!")
            st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_sesion, 2)} puntos!")
            st.table(pd.DataFrame(tabla_resumen))
            
    except Exception as e:
        st.error("Error al procesar el archivo FIT.")

# 6. RANKING Y GRÁFICA
st.divider()
st.subheader("🏆 Clasificación General")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales']).round(2)
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        
        # Ranking visual empezando en 1
        ranking_vis = ranking.copy()
        ranking_vis.index = ranking_vis.index + 1
        st.dataframe(ranking_vis, use_container_width=True)

        # Gráfica Horizontal con etiquetas
        chart = alt.Chart(ranking).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Puntos Totales:Q', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', axis=alt.Axis(labelColor='white', titleColor='white')),
        )
        
        text = chart.mark_text(align='left', baseline='middle', dx=5, color='white', fontWeight='bold').encode(text='Puntos Totales:Q')
        
        st.altair_chart((chart + text).properties(height=alt.Step(40), background='transparent').configure_axis(grid=False), use_container_width=True)
except:
    st.info("Sincronizando...")
