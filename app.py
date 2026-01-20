import streamlit as st
import fitparse
import pandas as pd
from io import BytesIO

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Reto Ciclista - Corazón de Hierro", layout="centered")

# Logotipo
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)

st.title("🏆 Reto: Corazón de Hierro")
st.markdown("Calcula tu esfuerzo mensual basado en la intensidad de tu pulso.")

# 2. BASE DE DATOS TEMPORAL
if 'db_ranking' not in st.session_state:
    st.session_state.db_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])

# 3. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()
uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando actividad...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer zonas del archivo FIT
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            
            # Si no hay zonas, aplicamos estándar (FC Max 190) sin avisos molestos
            if len(z_limits) < 4:
                z_limits = [114, 133, 152, 171, 220]

            # Extraer datos de frecuencia cardíaca
            hr_data = []
            for record in fitfile.get_messages('record'):
                hr = record.get_value('heart_rate')
                if hr: hr_data.append(hr)

            if hr_data:
                # Definición de multiplicadores y nombres
                config_zonas = {
                    "Z1 (Recuperación)": {"lim": z_limits[0], "mult": 1.0},
                    "Z2 (Fondo)": {"lim": z_limits[1], "mult": 1.5},
                    "Z3 (Tempo)": {"lim": z_limits[2], "mult": 3.0},
                    "Z4 (Umbral)": {"lim": z_limits[3], "mult": 5.0},
                    "Z5 (Máximo)": {"lim": 999, "mult": 10.0}
                }

                # Contadores de tiempo por zona (en segundos)
                segundos_zona = {z: 0 for z in config_zonas}
                
                for hr in hr_data:
                    for nombre, conf in config_zonas.items():
                        if hr <= conf["lim"]:
                            segundos_zona[nombre] += 1
                            break

                # Preparar desglose de resultados
                desglose_data = []
                puntos_totales_actividad = 0
                
                for nombre, segs in segundos_zona.items():
                    mins = segs / 60
                    pts = mins * config_zonas[nombre]["mult"]
                    puntos_totales_actividad += pts
                    if segs > 0: # Solo mostrar zonas donde hubo actividad
                        desglose_data.append({
                            "Zona": nombre,
                            "Tiempo": f"{int(mins)} min {int(segs % 60)} seg",
                            "Puntos": round(pts, 2)
                        })

                # --- MOSTRAR RESULTADOS DE LA ACTIVIDAD ---
                st.success(f"✅ ¡Actividad procesada para {nombre_usuario}!")
                
                col1, col2 = st.columns(2)
                col1.metric("Puntos Actividad", f"{round(puntos_totales_actividad, 2)} pts")
                col2.metric("Pulsaciones Medias", f"{int(sum(hr_data)/len(hr_data))} bpm")

                st.write("**Desglose por zonas:**")
                st.table(pd.DataFrame(desglose_data))

                # Actualizar Ranking Global
                df = st.session_state.db_ranking
                if nombre_usuario in df['Ciclista'].values:
                    df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_totales_actividad
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_totales_actividad}])
                    st.session_state.db_ranking = pd.concat([df, nueva_fila], ignore_index=True)
                
            else:
                st.error("El archivo no tiene datos de frecuencia cardíaca.")
    except Exception as e:
        st.error(f"Error técnico: {e}")

# 4. CLASIFICACIÓN GENERAL
st.divider()
st.subheader("📊 Ranking Mensual")

ranking_final = st.session_state.db_ranking.sort_values(by='Puntos Totales', ascending=False)
st.dataframe(ranking_final, use_container_width=True, hide_index=True)

# 5. EXPORTAR DATOS
if not ranking_final.empty:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        ranking_final.to_excel(writer, index=False, sheet_name='Ranking')
    
    st.download_button(
        label="📥 Descargar Ranking Completo (Excel)",
        data=output.getvalue(),
        file_name="ranking_corazon_hierro.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
