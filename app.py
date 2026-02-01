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

# 2. CONEXIÓN A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Error de conexión con la base de datos.")

# 3. DISEÑO CSS PROFESIONAL (Fondo 70% negro, textos blancos y cargador rojo/español)
st.markdown("""
    <style>
    /* Fondo principal: Gris muy oscuro (aprox 70% negro) */
    .stApp {
        background-color: #1A1A1A;
    }
    
    /* Forzar texto blanco en toda la app para legibilidad */
    html, body, [data-testid="stWidgetLabel"], .stMarkdown, p, span, label, li {
        color: #FFFFFF !important;
    }
    
    /* Títulos en rojo Gure Ultra */
    h1, h2, h3 {
        color: #FF4B4B !important;
        text-align: center;
        font-weight: bold;
    }

    /* Estilo de los Inputs de texto */
    input {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
        border: 1px solid #FF4B4B !important;
        border-radius: 5px !important;
    }

    /* --- PERSONALIZACIÓN CAJA DE SUBIDA (ROJO Y ESPAÑOL) --- */
    section[data-testid="stFileUploader"] {
        background-color: #262730;
        border: 2px dashed #FF0000;
        border-radius: 15px;
        padding: 20px;
    }
    
    /* Color de letras en rojo dentro del cargador */
    section[data-testid="stFileUploader"] div div div div {
        color: #FF0000 !important;
    }

    /* Botón "Examinar" en español y rojo */
    section[data-testid="stFileUploader"] button span::before {
        content: "Buscar archivo .FIT";
        color: #FF0000 !important;
        font-size: 16px;
    }
    section[data-testid="stFileUploader"] button span {
        font-size: 0 !important;
    }

    /* Texto "Arrastra" en español y rojo */
    section[data-testid="stFileUploader"] section div span::before {
        content: "Arrastra tu actividad aquí";
        font-size: 16px;
        color: #FF0000 !important;
    }
    section[data-testid="stFileUploader"] section div span {
        font-size: 0 !important;
    }

    /* Aviso de advertencia naranja */
    .warning-box {
        background-color: #332200;
        border-left: 5px solid #FFA500;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }

    /* Estilo de tablas */
    .stTable {
        background-color: #2D2D2D !important;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. CABECERA Y LOGO
URL_LOGO = "https://gureultra.com/wp-content/uploads/2024/10/GURE_ULTRA_RED_white.png"
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(URL_LOGO, use_container_width=True)

st.markdown("<h1>Corazón de Hierro</h1>", unsafe_allow_html=True)

# 5. INSTRUCCIONES Y AVISO DE NOMBRE
st.markdown("""
    <div class="warning-box">
        <b>📋 REGLAS DEL RETO:</b><br>
        • Usa siempre <b>EL MISMO NOMBRE</b> para que tus puntos se acumulen.<br>
        • Periodo: <b>1 de febrero al 1 de marzo de 2026</b>.<br>
        • ❤️ <b>SAN VALENTÍN (14 Feb):</b> ¡Los puntos valen el <b>DOBLE</b>!
    </div>
    """, unsafe_allow_html=True)

# 6. PANEL DE ENTRADA
st.divider()
nombre_usuario = st.text_input("Introduce tu Nombre o Nickname:").strip().upper()

st.markdown("### 📤 Sube tu actividad")
uploaded_file = st.file_uploader("", type=["fit"], label_visibility="collapsed")

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Procesando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer Fecha y validar
            fecha_act = None
            for record in fitfile.get_messages('session'):
                if record.get_value('start_time'):
                    fecha_act = record.get_value('start_time').date()
                    break
            
            # Validación de rango de fechas
            inicio_reto = date(2026, 2, 1)
            fin_reto = date(2026, 3, 1)

            if not fecha_act or not (inicio_reto <= fecha_act <= fin_reto):
                st.error(f"❌ La actividad tiene fecha de {fecha_act}. Solo se aceptan archivos de febrero 2026.")
                st.stop()

            # Procesar Frecuencia Cardíaca
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]
            
            if hr_records:
                z_limits = [114, 133, 152, 171, 220]
                mults = [1.0, 1.5, 3.0, 5.0, 10.0]
                
                # Bonus San Valentín
                es_sv = (fecha_act.month == 2 and fecha_act.day == 14)
                factor = 2.0 if es_sv else 1.0
                
                desglose_data = []
                puntos_sesion = 0

                for i in range(5):
                    if i == 0: segs = sum(1 for hr in hr_records if hr <= z_limits[0])
                    elif i == 4: segs = sum(1 for hr in hr_records if hr > z_limits[3])
                    else: segs = sum(1 for hr in hr_records if z_limits[i-1] < hr <= z_limits[i])
                    
                    mins = segs / 60
                    pts_zona = mins * mults[i] * factor
                    puntos_sesion += pts_zona
                    
                    if segs > 0:
                        desglose_data.append({
                            "Zona": f"Z{i+1}",
                            "Tiempo": f"{int(mins)}m {int(segs%60)}s",
                            "Puntos": round(pts_zona, 2)
                        })

                # --- RESULTADOS VISUALES ---
                if es_sv:
                    st.balloons()
                    st.markdown("### ❤️ ¡BONUS SAN VALENTÍN ACTIVADO! (Puntos x2)")

                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_sesion, 2)} puntos!")
                
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("PUNTOS HOY", f"+{round(puntos_sesion, 2)}")
                col_m2.metric("FECHA", str(fecha_act))

                st.markdown("#### 📊 Desglose de la sesión")
                st.table(pd.DataFrame(desglose_data))

                # --- SINCRONIZACIÓN GOOGLE SHEETS ---
                df = conn.read(ttl=0)
                if df is None or df.empty:
                    df = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])
                
                df['Puntos Totales'] = pd.to_numeric(df['Puntos Totales'], errors='coerce').fillna(0.0)

                if nombre_usuario in df['Ciclista'].values:
                    idx = df[df['Ciclista'] == nombre_usuario].index
                    df.loc[idx, 'Puntos Totales'] += puntos_sesion
                else:
                    nueva_fila = pd.DataFrame({'Ciclista': [nombre_usuario], 'Puntos Totales': [puntos_sesion]})
                    df = pd.concat([df, nueva_fila], ignore_index=True)

                conn.update(data=df)
                st.toast("Ranking actualizado.")
                
                st.markdown("#### 📈 Gráfica de Pulso")
                st.line_chart(pd.DataFrame(hr_records, columns=['BPM']))
            else:
                st.error("El archivo no contiene datos de frecuencia cardíaca.")
    except Exception as e:
        st.error(f"Error al procesar el archivo FIT.")

# 7. RANKING GLOBAL
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
    st.info("Cargando clasificación...")
