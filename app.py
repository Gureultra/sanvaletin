import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date, timedelta
import altair as alt

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Gure Ultra | Ranking Corazón de Hierro",
    page_icon="🔥",
    layout="centered"
)

# 2. DISEÑO CSS "ULTRA FORCE" (Fondo 70% negro, textos blancos, caja roja/español)
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
        border-radius: 8px;
        margin-bottom: 20px;
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
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. AJUSTE DE ZONAS (Para que el cálculo sea real para cada usuario)
with st.expander("⚙️ Ajustar mis Zonas de Pulsaciones (Opcional)"):
    st.info("Configura aquí los límites de tus zonas para un cálculo preciso.")
    c1, c2, c3, c4 = st.columns(4)
    z1_max = c1.number_input("Fin Z1", value=114)
    z2_max = c2.number_input("Fin Z2", value=133)
    z3_max = c3.number_input("Fin Z3", value=152)
    z4_max = c4.number_input("Fin Z4", value=171)
    
    c5, c6 = st.columns(2)
    z5_max = c5.number_input("Fin Z5", value=185)
    z6_max = c6.number_input("Fin Z6", value=195)
    st.caption("Z7 se considera cualquier pulso por encima de Z6.")

# 6. PANEL DE ENTRADA
st.divider()
nombre_usuario = st.text_input("Introduce tu Nombre o Nickname:").strip().upper()

st.markdown("""
    <div class="warning-box">
        <b>⚠️ RECORDATORIO:</b> Usa siempre el mismo nombre para acumular puntos.<br>
        Las actividades deben ser del <b>1 de febrero al 1 de marzo de 2026</b>.
    </div>
    """, unsafe_allow_html=True)

uploaded_file = st.file_uploader("Subida", type=["fit"], label_visibility="collapsed")

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Analizando precisión del tiempo y pulsaciones...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Obtener fecha real
            fecha_act = None
            for record in fitfile.get_messages('session'):
                if record.get_value('start_time'):
                    fecha_act = record.get_value('start_time').date()
                    break
            
            # Validar fecha 2026
            if not fecha_act or not (date(2026, 2, 1) <= fecha_act <= date(2026, 3, 1)):
                st.error(f"❌ Archivo del {fecha_act}. Fuera del rango del reto.")
                st.stop()

            # --- MOTOR DE CÁLCULO DE TIEMPO REAL ---
            recs = []
            for record in fitfile.get_messages('record'):
                t = record.get_value('timestamp')
                hr = record.get_value('heart_rate')
                if t and hr:
                    recs.append({'time': t, 'hr': hr})
            
            if len(recs) > 1:
                # Baremo
                limits = [z1_max, z2_max, z3_max, z4_max, z5_max, z6_max]
                mults = [1.0, 1.5, 3.0, 5.0, 10.0, 10.0, 10.0] # Z1 a Z7
                
                # Inicializar contadores de segundos por zona
                secs_per_zone = [0.0] * 7
                
                for i in range(len(recs)-1):
                    # Calculamos el tiempo real entre este registro y el siguiente
                    delta = (recs[i+1]['time'] - recs[i]['time']).total_seconds()
                    # Evitamos saltos absurdos (pausas largas)
                    if delta > 10: delta = 1 
                    
                    hr = recs[i]['hr']
                    
                    # Asignación a zona
                    if hr <= limits[0]: secs_per_zone[0] += delta
                    elif hr <= limits[1]: secs_per_zone[1] += delta
                    elif hr <= limits[2]: secs_per_zone[2] += delta
                    elif hr <= limits[3]: secs_per_zone[3] += delta
                    elif hr <= limits[4]: secs_per_zone[4] += delta
                    elif hr <= limits[5]: secs_per_zone[5] += delta
                    else: secs_per_zone[6] += delta

                # Bonus San Valentín
                factor_sv = 2.0 if (fecha_act.month == 2 and fecha_act.day == 14) else 1.0
                
                puntos_actividad = 0
                desglose = []
                for i, segs in enumerate(secs_per_zone):
                    if segs > 0:
                        minutos = segs / 60
                        pts = minutos * mults[i] * factor_sv
                        puntos_actividad += pts
                        desglose.append({
                            "Zona": f"Zona {i+1}",
                            "Tiempo": f"{int(segs//60)}m {int(segs%60)}s",
                            "Puntos": round(pts, 2)
                        })

                # Sincronizar GSheets
                df = conn.read(ttl=0)
                if df is None or df.empty:
                    df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)
                if nombre_usuario in df['Ciclista'].values:
                    df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_actividad
                else:
                    new_row = pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [puntos_actividad]})
                    df = pd.concat([df, new_row], ignore_index=True)
                
                conn.update(data=df)

                # Feedback
                if factor_sv > 1: st.balloons(); st.markdown("### ❤️ ¡BONUS SAN VALENTÍN (x2)!")
                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_actividad, 2)} puntos!")
                st.table(pd.DataFrame(desglose))
            else:
                st.error("El archivo no tiene suficientes datos de pulso.")
    except Exception as e:
        st.error(f"Error al leer el archivo.")

# 7. RANKING Y GRÁFICA
st.divider()
st.subheader("🏆 Clasificación General")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales']).round(2)
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        
        # Tabla desde 1
        ranking_vis = ranking.copy()
        ranking_vis.index += 1
        st.dataframe(ranking_vis, use_container_width=True)

        # Gráfica Horizontal Blanca
        base = alt.Chart(ranking).encode(
            x=alt.X('Puntos Totales:Q', axis=alt.Axis(labelColor='white', titleColor='white')),
            y=alt.Y('Ciclista:N', sort='-x', axis=alt.Axis(labelColor='white', titleColor='white'))
        )
        chart = base.mark_bar(color="#FF4B4B")
        text = base.mark_text(align='left', baseline='middle', dx=5, color='white', fontWeight='bold').encode(text='Puntos Totales:Q')
        st.altair_chart((chart + text).properties(height=alt.Step(40), background='transparent').configure_axis(grid=False), use_container_width=True)
except:
    st.info("Sincronizando...")
