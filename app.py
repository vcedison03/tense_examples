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
    st.audio(audio_path)

    # Usamos una Key única para evitar conflictos en Render
    with st.form(key=f"form_pregunta_{idx}"):
      idioma = st.selectbox(
          "Idioma esperado en tu respuesta:",
          ["Español (es)", "Inglés (en)"],
          key=f"idioma_{idx}"
      )
      respuesta_usuario = st.text_input(
          "Escribe tu respuesta aquí:", 
          placeholder="Escribe lo que escuchaste...",
          key=f"resp_{idx}"
      )
      submitted = st.form_submit_button("Calificar respuesta")

      if submitted:
        if not respuesta_usuario.strip():
          st.warning("⚠️ Por favor escribe una respuesta antes de continuar.")
          st.session_state.to_advance = False
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
          
          # Guardamos el resultado temporalmente en el estado para mostrarlo fuera del form
          st.session_state.ultimo_resultado = {
              "similitud": similitud,
              "estado_str": estado_str,
              "es_espanol": es_espanol,
              "esperada": esperada,
              "oracion_actual": oracion_actual,
              "significado_es": significado_es
          }
          st.session_state.respondido_actual = True

    # Si ya se respondió esta pregunta, mostramos el resultado y el botón para avanzar fuera del formulario
    if st.session_state.get("respondido_actual", False):
        res_temp = st.session_state.ultimo_resultado
        st.success(f"Calificación de este punto: {res_temp['similitud']:.1f}% -> {res_temp['estado_str']}")
        if res_temp['es_espanol']:
          st.write(f"**Lo que se esperaba:** {res_temp['esperada']}")
          st.write(f"**Oración original (EN):** {res_temp['oracion_actual']}")
        else:
          st.write(f"**Lo que se esperaba:** {res_temp['oracion_actual']}")
          st.write(f"**Significado (ES):** {res_temp['significado_es']}")

        if st.button("Siguiente oración ➡️", key=f"sig_{idx}"):
          st.session_state.respondido_actual = False
          st.session_state.idx += 1
          st.rerun()

    st.markdown("---")
    if st.button("🛑 Terminar test y ver resultados anticipadamente", key=f"terminar_{idx}"):
      st.session_state.respondido_actual = False
      st.session_state.etapa = "resultados"
      st.rerun()

  else:
    st.session_state.etapa = "resultados"
    st.rerun()
