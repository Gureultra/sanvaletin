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

# 2. CONEXIÓN (Debe estar fuera de los condicionales para que no falle)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error crítico de conexión con Google Sheets. Revisa los Secrets.")

# 3. DISEÑO PROFESIONAL Y LEGIBLE
st.markdown("""
    <style>
    .stApp { background-color: #121212; }
    
    /* Forzar texto blanco en toda la app */
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label {
        color: #FFFFFF !important;
    }
    
    /* Títulos */
    h1, h2, h3 { color: #FF4B4B !important; text-align: center; }

    /* Campos de texto: Fondo gris claro y letra NEGRA para máxima legibilidad al escribir */
    input {
        background-color: #F0F2F6 !important;
        color: #000000 !important;
    }

    /* Cuadro de aviso naranja */
    .warning-box {
        background-color: #332200;
        border-left: 5px solid #FFA500;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. CABECERA
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"
st.image(URL_LOGO, width=250)
st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. INSTRUCCIONES IMPORTANTES
st.markdown("""
    <div class="warning-box">
        <b>⚠️ INSTRUCCIONES CRÍTICAS:</b><br>
        1. Usa siempre el <b>MISMO NOMBRE</b> (ej: JUAN_PEREZ) para acumular tus puntos.<br>
        2. Solo se aceptan actividades entre el <b>1 de febrero y el 1 de marzo</b>.<br>
        3. El archivo debe ser formato <b>.FIT</b> (Garmin, Wahoo, Strava).
    </div>
    """, unsafe_allow_html=True)

with st.expander("ℹ️ Ver Sistema de Puntos"):
    st.write("Puntos por minuto: Z1: 1 | Z2: 1.5 | Z3: 3 | Z4: 5 | Z5: 10")
    st.info("❤️ Bonus San Valentín (14 feb): Puntos x2")

# 6. PANEL DE SUBIDA
st.divider()
nombre_usuario = st.text_input("Escribe tu Nombre / Nickname:").strip().upper()
uploaded_file = st.file_uploader("Sube tu archivo .FIT", type=["fit"])

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Procesando y Sincronizando...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Validar Fecha
            fecha_act = None
            for record in fitfile.get_messages('session'):
                if record.get_value('start_time'):
                    fecha_act = record.get_value('start_time').date()
                    break
            
            inicio_reto = date(2026, 2, 1)
            fin_reto = date(2026, 3, 1)

            if not fecha_act or not (inicio_reto <= fecha_act <= fin_reto):
                st.error(f"❌ Fecha {fecha_act} no válida para el reto actual.")
                st.stop()

            # Cálculo de Pulso
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]
            
            if hr_records:
                z_limits = [114, 133, 152, 171, 220]
                mults = [1.0, 1.5, 3.0, 5.0, 10.0]
                puntos_sesion = 0
                factor = 2.0 if (fecha_act.month == 2 and fecha_act.day == 14) else 1.0

                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    puntos_sesion += (segs / 60) * mults[i] * factor

                # --- SINCRONIZACIÓN CON GOOGLE SHEETS ---
                df = conn.read(ttl=0) # Leer datos frescos
                
                if df is None or df.empty:
                    df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                # Limpieza de datos para asegurar que son números
                df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)

                if nombre_usuario in df['Ciclista'].values:
                    # Sumar a usuario existente
                    idx = df[df['Ciclista'] == nombre_usuario].index
                    df.loc[idx, 'Puntos Totales'] = df.loc[idx, 'Puntos Totales'] + puntos_sesion
                else:
                    # Crear nuevo usuario
                    nueva_fila = pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [puntos_sesion]})
                    df = pd.concat([df, nueva_fila], ignore_index=True)

                # Actualizar la hoja de cálculo
                conn.update(data=df)
                
                st.success(f"✅ ¡Puntos sumados! +{round(puntos_sesion, 2)} para {nombre_usuario}")
                st.metric("TU APORTACIÓN HOY", f"{round(puntos_sesion, 2)} pts")
                st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))
            else:
                st.error("El archivo no tiene datos de frecuencia cardíaca.")
    except Exception as e:
        st.error(f"Error técnico: {e}")

# 7. RANKING EN TIEMPO REAL
st.divider()
st.subheader("🏆 Clasificación General")
try:
    ranking = conn.read(ttl=0)
    if ranking is not None and not ranking.empty:
        ranking['Puntos Totales'] = pd.to_numeric(ranking['Puntos Totales']).round(2)
        ranking = ranking.sort_values(by='Puntos Totales', ascending=False).reset_index(drop=True)
        ranking.index += 1
        st.dataframe(ranking, use_container_width=True)
except:
    st.info("Esperando datos del ranking...")
