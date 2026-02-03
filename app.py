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

# 2. DISEÑO CSS "BLACK & RED" (70% negro, textos blancos, caja roja/español)
st.markdown("""
    <style>
    .stApp { background-color: #1A1A1A !important; }
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li, h1, h2, h3 {
        color: #FFFFFF !important;
    }
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; font-weight: bold; }
    
    /* Input del nombre: Letra negra sobre fondo blanco para leer bien */
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
        padding: 10px;
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
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
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
st.image(URL_LOGO, width=220)
st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

st.markdown("""
    <div class="warning-box">
        <b>⚙️ DETECCIÓN AUTOMÁTICA:</b> La app lee las zonas de tu archivo FIT.<br>
        <b>🏆 PUNTUACIÓN:</b> Z1: 1 | Z2: 1.5 | Z3: 3 | Z4: 5 | <b>Z5, Z6, Z7: 10 pts</b>.<br>
        ❤️ <b>14 FEB:</b> Puntos Dobles. Ranking empieza en 1.
    </div>
    """, unsafe_allow_html=True)

# 5. PANEL DE ENTRADA
nombre_usuario = st.text_input("Introduce tu nombre exactamente igual que siempre:").strip().upper()
uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Extrayendo zonas y calculando puntos...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # --- 1. DETECCIÓN AUTOMÁTICA DE ZONAS DESDE EL ARCHIVO ---
            # Si no las encuentra, usará un estándar para no fallar
            detected_zones = []
            for msg in fitfile.get_messages('hr_zone'):
                high_bpm = msg.get_value('high_bpm')
                if high_bpm:
                    detected_zones.append(high_bpm)
            
            # Si el archivo no trae zonas (algunos no las exportan), usamos estándar 7 zonas
            if len(detected_zones) < 6:
                detected_zones = [114, 133, 152, 171, 185, 195] # Límites Z1-Z6

            # --- 2. CÁLCULO DE TIEMPO REAL (TIMESTAMP A TIMESTAMP) ---
            records = []
            for m in fitfile.get_messages('record'):
                ts = m.get_value('timestamp')
                hr = m.get_value('heart_rate')
                if ts and hr:
                    records.append({'t': ts, 'hr': hr})
            
            if len(records) > 1:
                # Inicializar 7 zonas
                secs_zones = [0.0] * 7
                points_map = [1.0, 1.5, 3.0, 5.0, 10.0, 10.0, 10.0]
                
                for i in range(len(records)-1):
                    delta = (records[i+1]['t'] - records[i]['t']).total_seconds()
                    if delta > 15: delta = 1 # Ignorar saltos por pausa
                    
                    hr = records[i]['hr']
                    # Clasificación en 7 zonas
                    if hr <= detected_zones[0]: secs_zones[0] += delta
                    elif hr <= detected_zones[1]: secs_zones[1] += delta
                    elif hr <= detected_zones[2]: secs_zones[2] += delta
                    elif hr <= detected_zones[3]: secs_zones[3] += delta
                    elif hr <= detected_zones[4]: secs_zones[4] += delta
                    elif hr <= detected_zones[5]: secs_zones[5] += delta
                    else: secs_zones[6] += delta

                # Fecha y Bonus San Valentín
                fecha_act = records[0]['t'].date()
                if not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
                    st.error(f"❌ Archivo del {fecha_act} fuera de rango.")
                    st.stop()

                bonus = 2.0 if (fecha_act.month == 2 and fecha_act.day == 14) else 1.0
                total_pts = 0
                resumen = []

                for z in range(7):
                    s = secs_zones[z]
                    if s > 0:
                        m = s / 60
                        p = m * points_map[z] * bonus
                        total_pts += p
                        resumen.append({
                            "Zona": f"Zona {z+1}",
                            "Tiempo": f"{int(s//60)}m {int(s%60)}s",
                            "Puntos": round(p, 2)
                        })

                # --- 3. ACTUALIZACIÓN DE RANKING ---
                df = conn.read(ttl=0)
                if df is None or df.empty:
                    df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)

                if nombre_usuario in df['Ciclista'].values:
                    df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += total_pts
                else:
                    df = pd.concat([df, pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [total_pts]})], ignore_index=True)
                
                conn.update(data=df)

                # --- 4. FEEDBACK VISUAL ---
                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(total_pts, 2)} puntos!")
                if bonus > 1: st.info("❤️ ¡BONUS DOBLE ACTIVADO!")
                st.table(pd.DataFrame(resumen))

            else:
                st.error("El archivo no tiene suficientes datos de pulso.")
    except Exception as e:
        st.error(f"Error al procesar: {e}")

# 6. RANKING Y GRÁFICA FINAL
st.divider()
st.subheader("🏆 Clasificación General")
try:
    data = conn.read(ttl=0)
    if data is not None and not data.empty:
        data['Puntos Totales'] = pd.to_numeric(data['Puntos Totales']).round(2)
        ranking = data.sort_values('Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1 # Ranking empieza en 1
        
        st.dataframe(ranking, use_container_width=True)

        # Gráfica horizontal con puntos en las barras
        bars = alt.Chart(ranking).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Puntos Totales:Q', title='Puntos Totales', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', title='', axis=alt.Axis(labelColor='white', titleColor='white'))
        )
        labels = bars.mark_text(align='left', baseline='middle', dx=5, color='white', fontWeight='bold').encode(text='Puntos Totales:Q')
        
        st.altair_chart((bars + labels).properties(height=alt.Step(45)), use_container_width=True)
except:
    st.info("Esperando datos...")
