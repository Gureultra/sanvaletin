import streamlit as st
import fitparse
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date

# ... (Configuración de página y Estilos CSS se mantienen igual) ...

# 6. PANEL DE SUBIDA
st.markdown("### 📤 Sube tu actividad")
nombre_usuario = st.text_input("Tu Nombre / Nickname:", placeholder="Ejemplo: JUAN_PEREZ")
uploaded_file = st.file_uploader("Selecciona tu archivo .FIT de tu reloj", type=["fit"])

if uploaded_file and nombre_usuario:
    try:
        with st.spinner('Analizando datos de intensidad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Obtener la fecha de la actividad
            fecha_act = None
            for record in fitfile.get_messages('session'):
                fecha_act_raw = record.get_value('start_time')
                if fecha_act_raw:
                    # Convertir a objeto date para comparar solo día/mes/año
                    fecha_act = fecha_act_raw.date()
                    break
            
            # 1. VALIDACIÓN DE RANGO DE FECHAS (1 Feb a 1 Mar)
            fecha_inicio_reto = date(2025, 2, 1) # Ajusta el año según corresponda
            fecha_fin_reto = date(2025, 3, 1)
            
            if not fecha_act or not (fecha_inicio_reto <= fecha_act <= fecha_fin_reto):
                st.error(f"❌ Fecha no válida: {fecha_act if fecha_act else 'Desconocida'}")
                st.warning("Solo se permiten actividades realizadas entre el 1 de febrero y el 1 de marzo.")
                st.stop() # Detiene la ejecución si la fecha es incorrecta

            # 2. CONTINUAR CON EL PROCESAMIENTO SI LA FECHA ES CORRECTA
            es_sv = (fecha_act.month == 2 and fecha_act.day == 14)
            hr_records = [r.get_value('heart_rate') for r in fitfile.get_messages('record') if r.get_value('heart_rate')]

            if hr_records:
                # ... (Lógica de cálculo de puntos y guardado en Google Sheets se mantiene igual) ...
                st.success(f"✅ Actividad del {fecha_act} aceptada.")
                # (Resto del código de cálculo...)
            else:
                st.error("No se detectaron datos de frecuencia cardíaca en el archivo.")

    except Exception as e:
        st.error(f"Error al procesar el archivo FIT.")

# ... (Resto de la app y Ranking) ...
