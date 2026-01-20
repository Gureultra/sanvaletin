import streamlit as st
import fitparse
import pandas as pd
from io import BytesIO

# 1. CONFIGURACIÓN DE PÁGINA E IMAGEN
st.set_page_config(page_title="Reto Ciclista - Corazón de Hierro", page_icon="🚴")

# Mostrar el logo desde el enlace proporcionado
st.image("https://drive.google.com/thumbnail?id=146rpaRwOGYAGXZMhzAY3iLKK07XrIAhn", width=200)

st.title("🏆 Reto: Corazón de Hierro")
st.markdown("""
Calcula tus puntos según el tiempo en cada zona cardíaca. 
**¡Usa siempre el mismo nombre para el ranking!**
""")

# 2. BASE DE DATOS TEMPORAL (Se mantiene mientras la app esté abierta)
if 'db_ranking' not in st.session_state:
    st.session_state.db_ranking = pd.DataFrame(columns=['Ciclista', 'Puntos Totales'])

# 3. ENTRADA DE USUARIO
nombre_usuario = st.text_input("Tu Nombre / Nickname:").strip().upper()

uploaded_file = st.file_uploader("Sube tu archivo .fit", type=["fit"])

if uploaded_file is not None and nombre_usuario != "":
    try:
        with st.spinner('Analizando zonas y pulsaciones...'):
            fitfile = fitparse.FitFile(uploaded_file)
            
            # Extraer zonas del archivo FIT
            z_limits = []
            for record in fitfile.get_messages('hr_zone'):
                val = record.get_value('high_value')
                if val: z_limits.append(val)
            
            # Si el archivo no tiene zonas, aplicamos estándar (FC Max 190)
            if len(z_limits) < 4:
                z_limits = [114, 133, 152, 171, 220]
                st.warning("⚠️ No se detectaron zonas en el archivo. Se han aplicado zonas estándar.")

            # Extraer datos de frecuencia cardíaca
            hr_data = []
            for record in fitfile.get_messages('record'):
                hr = record.get_value('heart_rate')
                if hr: hr_data.append(hr)

            if hr_data:
                # Lógica de puntos: minutos * multiplicador
                def obtener_mult(hr):
                    if hr <= z_limits[0]: return 1.0   # Z1
                    if hr <= z_limits[1]: return 1.5   # Z2
                    if hr <= z_limits[2]: return 3.0   # Z3
                    if hr <= z_limits[3]: return 5.0   # Z4
                    return 10.0                        # Z5

                # Cálculo: (segundos / 60) * multiplicador
                puntos_actividad = sum(obtener_mult(hr) for hr in hr_data) / 60

                # Actualizar el ranking en la sesión actual
                df = st.session_state.db_ranking
                if nombre_usuario in df['Ciclista'].values:
                    df.loc[df['Ciclista'] == nombre_usuario, 'Puntos Totales'] += puntos_actividad
                else:
                    nueva_fila = pd.DataFrame([{'Ciclista': nombre_usuario, 'Puntos Totales': puntos_actividad}])
                    st.session_state.db_ranking = pd.concat([df, nueva_fila], ignore_index=True)
                
                st.success(f"✅ ¡{nombre_usuario}, has sumado {round(puntos_actividad, 2)} puntos!")
            else:
                st.error("El archivo no contiene datos de pulso.")
    except Exception as e:
        st.error(f"Error al procesar: {e}")

# 4. TABLA DE CLASIFICACIÓN
st.divider()
st.subheader("📊 Ranking Actual")

ranking_mostrar = st.session_state.db_ranking.sort_values(by='Puntos Totales', ascending=False)
st.dataframe(ranking_mostrar, use_container_width=True, hide_index=True)

# 5. BOTÓN DE DESCARGA (Para que tú guardes el ranking final)
if not ranking_mostrar.empty:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        ranking_mostrar.to_excel(writer, index=False, sheet_name='Ranking')
    
    st.download_button(
        label="📥 Descargar Ranking (Excel)",
        data=output.getvalue(),
        file_name="ranking_reto_ciclista.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.info("Nota: Este ranking es temporal. Como administrador, descarga el Excel para guardar los puntos totales del mes.")
