import os
import sys
import time
import logging
import litellm
from litellm.exceptions import RateLimitError
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# Silenciar logs internos de litellm y crewai
for _logger in ("LiteLLM", "litellm", "litellm.proxy", "crewai", "opentelemetry"):
    logging.getLogger(_logger).setLevel(logging.CRITICAL)

# Reintentos automáticos ante Rate Limit (Groq free tier: 12 000 TPM)
litellm.num_retries = 10       # litellm reintenta cada llamada LLM hasta 10 veces
litellm.request_timeout = 120  # timeout generoso para dejar tiempo al backoff

# 1. Configurar el LLM según el backend elegido en el .bat
_backend = os.environ.get("EVALUADOR_BACKEND", "groq").lower()

if _backend == "lmstudio":
    _lmstudio_url = os.environ.get("LMSTUDIO_URL", "http://localhost:1234/v1")
    llm_gratis = LLM(
        model="openai/local",
        base_url=_lmstudio_url,
        api_key="lm-studio",
        temperature=0.3,
        max_tokens=800
    )
    print(f"[INFO] Backend: LM Studio ({_lmstudio_url})")
else:
    _groq_api_key = os.environ.get("GROQ_API_KEY", "")
    if not _groq_api_key:
        print("[ERROR] No se encontró GROQ_API_KEY.")
        print("        Crea un archivo .env con: GROQ_API_KEY=tu_clave")
        print("        Obtén tu clave gratis en: https://console.groq.com")
        sys.exit(1)
    llm_gratis = LLM(
        model="groq/llama-3.1-8b-instant",   # 30k TPM vs 12k del 70B → menos rate limits
        temperature=0.3,
        max_tokens=800
    )
    print("[INFO] Backend: Groq (Llama 3.1 8B Instant)")

# 2. Textos de entrada (leídos desde la carpeta inputs/)

RUTA_CV     = os.path.join(os.path.dirname(__file__), "inputs", "cv.txt")
RUTA_OFERTA = os.path.join(os.path.dirname(__file__), "inputs", "oferta.txt")

def leer_archivo(ruta, nombre):
    if not os.path.exists(ruta):
        print(f"[ERROR] No se encontró el archivo: {ruta}")
        sys.exit(1)
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read().strip()
    if not contenido or contenido.startswith("Pega aquí"):
        print(f"[ERROR] El archivo '{nombre}' está vacío o contiene el texto de ejemplo.")
        print(f"        Edítalo con tu contenido real: {ruta}")
        sys.exit(1)
    return contenido

mi_cv        = leer_archivo(RUTA_CV,     "cv.txt")
oferta_empleo = leer_archivo(RUTA_OFERTA, "oferta.txt")

# 3. Creación de los 4 Agentes Evaluadores

agente_ats = Agent(
    role='Especialista en ATS y Palabras Clave',
    goal='Identificar qué palabras clave críticas de la oferta están ausentes o presentes en el CV.',
    backstory=(
        'Experto en ATS con 10 años de experiencia. '
        'Clasifica keywords en OBLIGATORIAS y DESEABLES. '
        'No inventes keywords. No evalúes soft skills. Sé conciso. '
        'Puntuación de 0 a 10 según cobertura de keywords obligatorias.'
    ),
    verbose=False,
    allow_delegation=False,
    max_iter=3,
    llm=llm_gratis
)

agente_tech_lead = Agent(
    role='Tech Lead Senior Full-Stack',
    goal='Evaluar la profundidad técnica real del candidato basándose en proyectos y logros concretos.',
    backstory=(
        'Tech Lead Senior con 15 años de experiencia. '
        'Evalúas: complejidad de proyectos, profundidad técnica y años de experiencia relevante. '
        'NO resumas el CV. NO inventes datos. '
        'Máx. 3 fortalezas y 3 brechas con evidencia. Puntuación técnica 0-10.'
    ),
    verbose=False,
    allow_delegation=False,
    max_iter=3,
    llm=llm_gratis
)

agente_rrhh = Agent(
    role='Reclutador de Recursos Humanos',
    goal='Evaluar estabilidad laboral, idiomas, habilidades blandas y encaje cultural del candidato.',
    backstory=(
        'Reclutadora senior con 12 años en perfiles tecnológicos. '
        'Evalúas: estabilidad laboral, idiomas requeridos vs declarados, soft skills y encaje cultural. '
        'No evalúes aspectos técnicos. Basa cada punto en evidencia del CV. '
        'Puntuación de encaje humano 0-10.'
    ),
    verbose=False,
    allow_delegation=False,
    max_iter=3,
    llm=llm_gratis
)

agente_juez = Agent(
    role='Director de Contratación (Juez Final)',
    goal='Consolidar los informes del equipo y emitir veredicto final con 3 consejos específicos.',
    backstory=(
        'Director de Ingeniería que decide tras leer los informes de ATS, Tech Lead y RRHH. '
        'Veredicto: puntuación ponderada (ATS 30% + Técnico 50% + RRHH 20%), dictamen y 3 consejos urgentes. '
        'REGLA CRÍTICA: cada consejo DEBE citar un elemento textual real del CV (sección, bullet o frase concreta). '
        'PROHIBIDO: consejos genéricos sin citar qué texto cambiar y cómo. '
        'Sé directo, frío y constructivo.'
    ),
    verbose=False,
    allow_delegation=False,
    max_iter=3,
    llm=llm_gratis
)

# 4. Creación de las Tareas (Lo que debe hacer cada agente)

tarea_ats = Task(
    description=(
        f'OFERTA DE EMPLEO:\n{oferta_empleo}\n\n'
        f'CV DEL CANDIDATO:\n{mi_cv}\n\n'
        'INSTRUCCIONES:\n'
        '1. Extrae todas las keywords técnicas (tecnologías, lenguajes, herramientas, certificaciones) de la oferta.\n'
        '2. Clasifícalas en OBLIGATORIAS y DESEABLES según el tono de la oferta.\n'
        '3. Indica cuáles están PRESENTES y cuáles están AUSENTES en el CV.\n'
        '4. Asigna una puntuación ATS de 0 a 10 basada en la cobertura de keywords obligatorias.'
    ),
    expected_output=(
        'KEYWORDS OBLIGATORIAS: [presente ✓ / ausente ✗ por cada una]\n'
        'KEYWORDS DESEABLES: [presente ✓ / ausente ✗ por cada una]\n'
        'PUNTUACIÓN ATS: X/10 — [una línea de justificación]'
    ),
    agent=agente_ats
)

tarea_tech = Task(
    description=(
        f'OFERTA DE EMPLEO:\n{oferta_empleo}\n\n'
        f'CV DEL CANDIDATO:\n{mi_cv}\n\n'
        'INSTRUCCIONES:\n'
        '1. Evalúa la complejidad real de los proyectos descritos en el CV (¿son de nivel junior, mid o senior?).\n'
        '2. Evalúa la profundidad en las tecnologías clave que exige la oferta.\n'
        '3. Evalúa si los años de experiencia relevante son suficientes para el rol.\n'
        '4. Lista máximo 3 fortalezas técnicas concretas y máximo 3 brechas técnicas reales.\n'
        '5. Asigna una puntuación técnica de 0 a 10 con justificación de una línea.'
    ),
    expected_output=(
        'FORTALEZAS: [máx. 3 puntos con evidencia del CV]\n'
        'BRECHAS: [máx. 3 puntos con referencia a la oferta]\n'
        'PUNTUACIÓN TÉCNICA: X/10 — [una línea de justificación]'
    ),
    agent=agente_tech_lead
)

tarea_rrhh = Task(
    description=(
        f'OFERTA DE EMPLEO:\n{oferta_empleo}\n\n'
        f'CV DEL CANDIDATO:\n{mi_cv}\n\n'
        'INSTRUCCIONES:\n'
        '1. Calcula el tiempo medio de permanencia en cada empresa y valora la estabilidad laboral.\n'
        '2. Compara los idiomas declarados en el CV con los requeridos en la oferta.\n'
        '3. Identifica habilidades blandas inferidas del CV (liderazgo, autonomía, comunicación, etc.).\n'
        '4. Evalúa el encaje cultural: ¿el perfil encaja con el tipo de empresa de la oferta?\n'
        '5. Asigna una puntuación de encaje humano de 0 a 10 con justificación de una línea.'
    ),
    expected_output=(
        'ESTABILIDAD: [tiempo medio por empresa + valoración]\n'
        'IDIOMAS: [requerido vs declarado]\n'
        'SOFT SKILLS: [lista breve]\n'
        'ENCAJE CULTURAL: [una línea]\n'
        'PUNTUACIÓN RRHH: X/10 — [una línea de justificación]'
    ),
    agent=agente_rrhh
)

tarea_veredicto = Task(
    description=(
        'Recibes los informes del Especialista ATS, el Tech Lead y la Reclutadora de RRHH.\n'
        'INSTRUCCIONES:\n'
        '1. Calcula la puntuación global ponderada: (Puntuación ATS × 0.30) + (Puntuación Técnica × 0.50) + (Puntuación RRHH × 0.20). Muestra el cálculo.\n'
        '2. Emite un dictamen: PASA A ENTREVISTA (≥70%), EN LISTA DE ESPERA (50-69%) o DESCARTADO (<50%).\n'
        '3. Redacta exactamente 3 consejos concretos y urgentes para mejorar el CV.\n'
        '   - Consejo 1: debe indicar qué keyword o tecnología concreta añadir y en qué experencia o sección del CV encajaría.\n'
        '   - Consejo 2: debe señalar una sección o bullet concreto del CV que necesita ser reformulado, y proponer cómo hacerlo.\n'
        '   - Consejo 3: debe identificar un elemento textual concreto del CV (sección, bullet, dato) que resta impacto o es irrelevante para este rol, y explicar exactamente qué hacer con él (eliminar, condensar o sustituir y por qué).\n'
        '   PROHIBIDO: consejos genéricos sin citar elementos reales del CV.'
    ),
    expected_output=(
        'CÁLCULO: ATS(X×0.30) + Técnico(X×0.50) + RRHH(X×0.20) = XX%\n'
        'DICTAMEN: [PASA A ENTREVISTA / EN LISTA DE ESPERA / DESCARTADO]\n'
        'CONSEJOS URGENTES:\n'
        '  1. [Consejo citando elemento textual real del CV]\n'
        '  2. [Consejo citando elemento textual real del CV]\n'
        '  3. [Consejo citando elemento textual real del CV]'
    ),
    context=[tarea_ats, tarea_tech, tarea_rrhh],
    agent=agente_juez
)

# --- Agente 5: Coach de Prompts ---
agente_coach = Agent(
    role='Coach de CV y Prompt Engineer',
    goal='Convertir cada consejo del veredicto en un prompt listo para ChatGPT/Claude y una micro-acción directa.',
    backstory=(
        'Experto en CVs y prompt engineering. '
        'Para cada consejo generas: (1) prompt auto-contenido con marcador [PEGA AQUÍ TU TEXTO] '
        'para implementarlo en menos de 5 minutos, y (2) micro-acción de edición de una línea. '
        'Sé práctico y directo. No repitas el consejo.'
    ),
    verbose=False,
    allow_delegation=False,
    max_iter=3,
    llm=llm_gratis
)

tarea_coach = Task(
    description=(
        f'CV DEL CANDIDATO:\n{mi_cv}\n\n'
        'Recibes el veredicto final del Director de Contratación con 3 consejos urgentes.\n'
        'INSTRUCCIONES:\n'
        'Para cada uno de los 3 consejos, genera DOS cosas:\n'
        '  A) PROMPT IA: un prompt listo para copiar en ChatGPT/Claude que permita implementar el consejo en menos de 5 minutos. '
        'El prompt debe incluir las instrucciones exactas y un marcador [PEGA AQUÍ TU TEXTO] donde el usuario insertará su contenido real.\n'
        '  B) MICRO-ACCIÓN: una instrucción de edición directa de una sola línea (ej: "Ve al bullet X de la empresa Y y cámbialo por...").\n'
        'Usa el CV real del candidato para que los prompts sean específicos, no genéricos.'
    ),
    expected_output=(
        'HERRAMIENTAS PARA MEJORAR EL CV:\n'
        'CONSEJO 1\n'
        '  → Prompt: "[prompt con marcador [PEGA AQUÍ TU TEXTO]]"\n'
        '  → Acción: [edición de una línea]\n'
        'CONSEJO 2\n'
        '  → Prompt: "[prompt con marcador [PEGA AQUÍ TU TEXTO]]"\n'
        '  → Acción: [edición de una línea]\n'
        'CONSEJO 3\n'
        '  → Prompt: "[prompt con marcador [PEGA AQUÍ TU TEXTO]]"\n'
        '  → Acción: [edición de una línea]'
    ),
    context=[tarea_veredicto],
    agent=agente_coach
)

# 5. Formar el Equipo y Ejecutar
# Pausa de 5s entre tareas solo con Groq para no saturar el límite de TPM
_task_callback = (lambda _: time.sleep(5)) if _backend != "lmstudio" else None

comite_evaluador = Crew(
    agents=[agente_ats, agente_tech_lead, agente_rrhh, agente_juez, agente_coach],
    tasks=[tarea_ats, tarea_tech, tarea_rrhh, tarea_veredicto, tarea_coach],
    process=Process.sequential,
    verbose=False,
    task_callback=_task_callback
)

# Iniciar la evaluación
print()
print("╔══════════════════════════════════════════════╗")
print("║       COMITÉ DE IAS — EVALUACIÓN DE CV       ║")
print("╚══════════════════════════════════════════════╝")
print()
print("  Los 5 agentes están evaluando el CV...")
print("  (Esto puede tardar entre 45 y 90 segundos)")
print()

_MAX_CREW_RETRIES = 5
resultado_crew = None
for _intento in range(1, _MAX_CREW_RETRIES + 1):
    try:
        resultado_crew = comite_evaluador.kickoff()
        break
    except RateLimitError as _e:
        if _intento < _MAX_CREW_RETRIES:
            _espera = 30 * _intento
            print(f"  [Rate limit] Groq necesita descansar. Reintentando en {_espera}s... "
                  f"(intento {_intento}/{_MAX_CREW_RETRIES})")
            time.sleep(_espera)
        else:
            print("  [ERROR] Se agotaron los reintentos por Rate Limit de Groq.")
            print("  Consejo: espera 1 minuto y vuelve a ejecutar el evaluador.")
            raise

# El crew devuelve el output de la última tarea (tarea_coach).
# Recuperamos también el output del veredicto desde el task directamente.
veredicto_output = tarea_veredicto.output.raw if tarea_veredicto.output else ""
coach_output    = tarea_coach.output.raw    if tarea_coach.output    else str(resultado_crew)

print()
print("╔══════════════════════════════════════════════╗")
print("║       VEREDICTO FINAL DEL COMITÉ DE IAS      ║")
print("╚══════════════════════════════════════════════╝")
print()
print(veredicto_output)
print()
print("╔══════════════════════════════════════════════╗")
print("║   HERRAMIENTAS PARA MEJORAR EL CV (COACH)    ║")
print("╚══════════════════════════════════════════════╝")
print()
print(coach_output)
print()