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
    layout="wide"
)

# 2. DISEÑO CSS (Fondo 70% negro, textos blancos, inputs legibles)
st.markdown("""
    <style>
    .stApp { background-color: #1A1A1A !important; }
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3 {
        color: #FFFFFF !important;
    }
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; font-weight: bold; }
    
    /* Input del nombre: Fondo blanco, letras NEGRAS para leer bien */
    input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold;
    }

    /* Caja de subida personalizada en ROJO */
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
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Error de conexión con la base de datos.")

# 4. CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"
st.image(URL_LOGO, width=200)
st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. CONFIGURACIÓN DE ZONAS (CRÍTICO PARA EL CÁLCULO)
st.markdown("### ⚙️ Configura tus Zonas de FC")
st.write("Ajusta los límites superiores de cada zona según tu prueba de esfuerzo:")
c1, c2, c3, c4, c5, c6 = st.columns(6)
lim_z1 = c1.number_input("Fin Z1", value=114)
lim_z2 = c2.number_input("Fin Z2", value=133)
lim_z3 = c3.number_input("Fin Z3", value=152)
lim_z4 = c4.number_input("Fin Z4", value=171)
lim_z5 = c5.number_input("Fin Z5", value=185)
lim_z6 = c6.number_input("Fin Z6", value=195)
# Z7 es > lim_z6

# 6. PANEL DE SUBIDA
st.divider()
nombre_usuario = st.text_input("Introduce tu Nombre o Nickname:").strip().upper()
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Calculando puntos...'):
            fitfile = fitparse.FitFile(uploaded_file)
            messages = list(fitfile.get_messages('record'))
            
            # Obtener fecha
            fecha_act = None
            for msg in fitfile.get_messages('session'):
                fecha_act = msg.get_value('start_time').date()
                break
            
            if not fecha_act or not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
                st.error(f"❌ Fecha {fecha_act} no válida (Solo Feb 2026).")
                st.stop()

            # MOTOR DE CÁLCULO PRECISO
            segundos_zonas = {1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0}
            puntos_baremo = {1:1, 2:1.5, 3:3, 4:5, 5:10, 6:10, 7:10}
            
            last_ts = None
            for m in messages:
                ts = m.get_value('timestamp')
                hr = m.get_value('heart_rate')
                if ts and hr:
                    if last_ts:
                        delta = (ts - last_ts).total_seconds()
                        if 0 < delta < 15: # Evitar saltos por pausas
                            if hr <= lim_z1: segundos_zonas[1] += delta
                            elif hr <= lim_z2: segundos_zonas[2] += delta
                            elif hr <= lim_z3: segundos_zonas[3] += delta
                            elif hr <= lim_z4: segundos_zonas[4] += delta
                            elif hr <= lim_z5: segundos_zonas[5] += delta
                            elif hr <= lim_z6: segundos_zonas[6] += delta
                            else: segundos_zonas[7] += delta
                    last_ts = ts

            # Bonus San Valentín
            bonus = 2.0 if (fecha_act.month == 2 and fecha_act.day == 14) else 1.0
            total_pts = 0
            tabla_resumen = []

            for z in range(1, 8):
                segs = segundos_zonas[z]
                if segs > 0:
                    pts = (segs / 60) * puntos_baremo[z] * bonus
                    total_pts += pts
                    tabla_resumen.append({
                        "Zona": f"Zona {z}",
                        "Tiempo": f"{int(segs//60)}m {int(segs%60)}s",
                        "Puntos": round(pts, 2)
                    })

            # Guardar y Mostrar
            df = conn.read(ttl=0)
            if df is None or df.empty: df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
            df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0)
            
            if nombre_usuario in df['Ciclista'].values:
                df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += total_pts
            else:
                df = pd.concat([df, pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [total_pts]})], ignore_index=True)
            
            conn.update(data=df)
            
            st.success(f"✅ ¡Puntos sumados! Total sesión: {round(total_pts, 2)}")
            if bonus > 1: st.warning("❤️ BONUS DOBLE APLICADO")
            st.table(pd.DataFrame(tabla_resumen))

    except Exception as e:
        st.error(f"Error al leer el archivo. Asegúrate de que tenga pulso.")

# 7. RANKING Y GRÁFICA CORREGIDA
st.divider()
st.subheader("🏆 Clasificación General")
try:
    data = conn.read(ttl=0)
    if data is not None and not data.empty:
        data['Puntos Totales'] = pd.to_numeric(data['Puntos Totales']).round(2)
        ranking = data.sort_values('Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1 # Empezar en 1
        
        st.dataframe(ranking, use_container_width=True)

        st.markdown("### 📊 Comparativa de Esfuerzo")
        
        # Gráfica Altair con textos blancos forzados
        bars = alt.Chart(ranking).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Puntos Totales:Q', title='Puntos Totales', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', title='', axis=alt.Axis(labelColor='white', titleColor='white'))
        )
        
        text = bars.mark_text(align='left', baseline='middle', dx=5, color='white', fontWeight='bold').encode(
            text='Puntos Totales:Q'
        )
        
        st.altair_chart((bars + text).properties(height=alt.Step(40)).configure_view(strokeOpacity=0), use_container_width=True)
except:
    st.info("No hay datos en el ranking todavía.")
