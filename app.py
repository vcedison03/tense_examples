import difflib
import random
import re
import time
from deep_translator import GoogleTranslator
from gtts import gTTS
import requests
import streamlit as st

st.set_page_config(
    page_title="Práctica de Inglés con Libros", page_icon="📚", layout="centered"
)

st.title("🎧 Práctica de Inglés: Test Interactivo")
st.write(
    "Practica tu comprensión auditiva escuchando fragmentos de libros clásicos y calificando tus respuestas."
)

# Inicializar estados de la sesión en Streamlit
if "etapa" not in st.session_state:
  st.session_state.etapa = "config"  # 'config', 'test', 'resultados'

if "historial" not in st.session_state:
  st.session_state.historial = []

if "idx" not in st.session_state:
  st.session_state.idx = 0

if "oraciones" not in st.session_state:
  st.session_state.oraciones = []

if "configuracion" not in st.session_state:
  st.session_state.configuracion = {}

# ==========================================
# ETAPA 1: CONFIGURACIÓN
# ==========================================
if st.session_state.etapa == "config":
  st.header("⚙️ Configuración del Test")

  tipo_exigencia = st.selectbox(
      "Nivel de exigencia:", ["Medio (75%)", "Estricto (90%)", "Flexible (60%)"]
  )

  op_tema = st.selectbox(
      "Categoría de libros:",
      [
          "Physics & Electromagnetism",
          "Astronomy & Space",
          "Technology & Computing",
          "Philosophy & Logic",
          "Escribir tema personalizado",
      ],
  )

  tema_personalizado = ""
  if op_tema == "Escribir tema personalizado":
    tema_personalizado = st.text_input(
        "Escribe tu tema en inglés (ej: history, biology):"
    )

  col1, col2 = st.columns(2)
  with col1:
    min_palabras = st.number_input(
        "Cantidad mínima de palabras", min_value=3, max_value=25, value=6
    )
  with col2:
    max_palabras = st.number_input(
        "Cantidad máxima de palabras", min_value=4, max_value=30, value=12
    )

  if st.button("🚀 Cargar libro e iniciar test", type="primary"):
    # Mapear exigencia
    if "Estricto" in tipo_exigencia:
      umbral = 90.0
    elif "Flexible" in tipo_exigencia:
      umbral = 60.0
    else:
      umbral = 75.0

    # Mapear tema
    temas_map = {
        "Physics & Electromagnetism": "physics",
        "Astronomy & Space": "astronomy",
        "Technology & Computing": "technology",
        "Philosophy & Logic": "philosophy",
    }
    tema = (
        tema_personalizado
        if op_tema == "Escribir tema personalizado" and tema_personalizado
        else temas_map.get(op_tema, "science")
    )

    with st.spinner(f"Buscando libros sobre '{tema}'..."):
      try:
        res = requests.get(
            f"https://gutendex.com/books/?search={tema}&languages=en",
            timeout=25,
        ).json()
        libros = res.get("results", [])
      except Exception as e:
        st.error(f"Error de red: {e}")
        libros = []

    if not libros:
      st.error(
          "No se encontraron libros para este tema. Intenta con otro término."
      )
    else:
      libro = random.choice(libros)
      titulo = libro.get("title", "Desconocido")
      text_url = libro.get("formats", {}).get(
          "text/plain; charset=us-ascii"
      ) or libro.get("formats", {}).get("text/plain; charset=utf-8")

      if not text_url:
        st.error("El libro seleccionado no tiene texto disponible.")
      else:
        with st.spinner(f"Descargando y procesando '{titulo}'..."):
          raw_text = requests.get(text_url, timeout=20).text
          text_clean = re.sub(r"\s+", " ", raw_text)
          oraciones = [
              o.strip()
              for o in re.split(r"(?<=[.!?])\s+", text_clean)
              if min_palabras <= len(o.split()) <= max_palabras
          ]

        if not oraciones:
          st.warning(
              "No se encontraron oraciones con esa longitud en este libro. Prueba"
              " ampliando el rango de palabras."
          )
        else:
          random.shuffle(oraciones)
          st.session_state.oraciones = oraciones[:15]  # Tomamos hasta 15
          st.session_state.configuracion = {
              "titulo": titulo,
              "tipo_exigencia": tipo_exigencia,
              "umbral": umbral,
          }
          st.session_state.idx = 0
          st.session_state.historial = []
          st.session_state.etapa = "test"
          st.rerun()

# ==========================================
# ETAPA 2: TEST INTERACTIVO
# ==========================================
elif st.session_state.etapa == "test":
  oraciones = st.session_state.oraciones
  idx = st.session_state.idx

  if idx < len(oraciones):
    oracion_actual = oraciones[idx]

    st.progress(
        (idx + 1) / len(oraciones),
        text=f"Pregunta {idx + 1} de {len(oraciones)}",
    )
    st.subheader(f"📚 Libro: {st.session_state.configuracion['titulo']}")

    # Generar audio con gTTS en tiempo real
    tts = gTTS(text=oracion_actual, lang="en")
    audio_path = f"temp_audio_{idx}.mp3"
    tts.save(audio_path)

    st.write("Escucha el audio y escribe lo que entendiste:")
    st.audio(audio_path, autoplay=True)

    with st.form(key=f"form_pregunta_{idx}" ):
      idioma = st.selectbox(
          "Idioma esperado en tu respuesta:",
          ["Español (es)", "Inglés (en)"],
      )
      respuesta_usuario = st.text_input(
          "Escribe tu respuesta aquí:", placeholder="Escribe lo que escuchaste..."
      )
      submitted = st.form_submit_button("Calificar respuesta")

      if submitted:
        if not respuesta_usuario.strip():
          st.warning("⚠️ Por favor escribe una respuesta antes de continuar.")
        else:
          es_espanol = "es" in idioma
          traductor = GoogleTranslator(source="en", target="es")

          esperada = ""
          significado_es = ""
          try:
            if es_espanol:
              esperada = traductor.translate(oracion_actual)
            else:
              significado_es = traductor.translate(oracion_actual)
          except Exception:
            esperada = oracion_actual
            significado_es = oracion_actual

          if es_espanol:
            similitud = (
                difflib.SequenceMatcher(
                    None, esperada.lower(), respuesta_usuario.lower()
                ).ratio()
                * 100
            )
          else:
            similitud = (
                difflib.SequenceMatcher(
                    None, oracion_actual.lower(), respuesta_usuario.lower()
                ).ratio()
                * 100
            )

          umbral = st.session_state.configuracion["umbral"]
          aprobado = similitud >= umbral
          estado_str = "[¡Aprobado!] ✅" if aprobado else "[Por debajo del nivel] ❌"

          # Guardar en historial de sesión
          st.session_state.historial.append({
              "n": idx + 1,
              "oracion": oracion_actual,
              "respuesta": respuesta_usuario,
              "calificacion": similitud,
              "estado_str": estado_str,
              "audio": audio_path,
              "esperada": esperada if es_espanol else oracion_actual,
              "significado": significado_es,
          })

          st.success(f"Calificación de este punto: {similitud:.1f}% -> {estado_str}")
          if es_espanol:
            st.write(f"**Lo que se esperaba:** {esperada}")
            st.write(f"**Oración original (EN):** {oracion_actual}")
          else:
            st.write(f"**Lo que se esperaba:** {oracion_actual}")
            st.write(f"**Significado (ES):** {significado_es}")

          st.session_state.idx += 1
          if st.button("Siguiente oración ➡️"):
            st.rerun()

    if st.button("🛑 Terminar test y ver resultados anticipadamente"):
      st.session_state.etapa = "resultados"
      st.rerun()

  else:
    st.session_state.etapa = "resultados"
    st.rerun()

# ==========================================
# ETAPA 3: RESULTADOS Y REVISIÓN
# ==========================================
elif st.session_state.etapa == "resultados":
  st.header("🏆 Resultados Finales y Revisión")

  historial = st.session_state.historial
  total = len(historial)
  aciertos = sum(
      1 for x in historial if "[¡Aprobado!]" in x["estado_str"]
  )
  promedio = (
      sum(x["calificacion"] for x in historial) / total if total > 0 else 0
  )

  st.write(f"📚 **Libro:** {st.session_state.configuracion['titulo']}")
  st.write(f"⚙️ **Nivel:** {st.session_state.configuracion['tipo_exigencia']}")
  st.write(f"📝 **Preguntas respondidas:** {total}")
  st.write(f"✅ **Aprobadas:** {aciertos}")
  st.write(f"📊 **Precisión promedio:** {promedio:.1f}%")

  st.markdown("---")
  st.subheader("📋 Listado detallado de oraciones practicadas")

  for item in historial:
    with st.expander(
        f"Oración #{item['n']} - Calificación: {item['calificacion']:.1f}%"
        f" {item['estado_str']}"
    ):
      st.write(f"**Original (EN):** {item['oracion']}")
      st.write(f"**Tu respuesta:** {item['respuesta']}")
      st.audio(item["audio"])

  if st.button("🔄 Volver a empezar"):
    st.session_state.etapa = "config"
    st.session_state.historial = []
    st.session_state.idx = 0
    st.rerun()
