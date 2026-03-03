# Comité de IAs — Evaluador de CV

Un sistema multiagente construido con **CrewAI** que evalúa un CV frente a una oferta de empleo usando 5 agentes especializados con IA.

## ¿Qué hace?

Lanza un comité de 5 agentes IA que analizan tu CV en paralelo y emiten un veredicto estructurado:

| Agente | Rol |
|---|---|
| 🔍 Especialista ATS | Detecta keywords obligatorias y deseables presentes/ausentes |
| 👨‍💻 Tech Lead Senior | Evalúa profundidad técnica, proyectos y brechas |
| 🤝 Reclutadora RRHH | Valora estabilidad, idiomas, soft skills y encaje cultural |
| ⚖️ Director de Contratación | Calcula puntuación ponderada y emite 3 consejos específicos |
| 🎯 Coach de CV | Genera prompts listos para usar en ChatGPT/Claude para aplicar cada consejo |

## Requisitos

- Python 3.11, 3.12 o 3.13
- Cuenta gratuita en [Groq](https://console.groq.com) **o** [LM Studio](https://lmstudio.ai) con un modelo cargado

## Instalación

```bash
# 1. Clona el repo
git clone https://github.com/tu-usuario/comite-ias-evaluador-cv.git
cd comite-ias-evaluador-cv

# 2. Copia el archivo de configuración y añade tu clave
copy .env.example .env
# Edita .env y pon tu GROQ_API_KEY

# 3. Instala dependencias
pip install -r requirements.txt
```

## Uso

1. Copia tu CV en `inputs/cv.txt` (texto plano)
2. Copia la oferta de empleo en `inputs/oferta.txt` (texto plano)
3. Ejecuta:

```bash
iniciar_evaluador.bat
```

Al arrancar te preguntará si usar **Groq** (nube, gratis) o **LM Studio** (local, sin internet).

## Resultado de ejemplo

```
CÁLCULO: ATS(6×0.30) + Técnico(7×0.50) + RRHH(8×0.20) = 6.9 → 69%
DICTAMEN: EN LISTA DE ESPERA

CONSEJOS URGENTES:
  1. Añadir "Salesforce Marketing Cloud" en la experiencia de Empresa X...
  2. Reformular el bullet "Lideré proyectos de datos" por "Lideré migración de..."
  3. Eliminar la sección "Hobbies" — no aporta valor para este rol técnico
```

## Estructura del proyecto

```
comite-ias-evaluador-cv/
├── evaluador_cv.py       # Lógica principal con los 5 agentes
├── iniciar_evaluador.bat # Lanzador Windows con selector de backend
├── requirements.txt      # Dependencias Python
├── .env.example          # Plantilla de configuración (sin claves reales)
└── inputs/
    ├── cv.txt.example    # Ejemplo de formato para el CV
    └── oferta.txt.example # Ejemplo de formato para la oferta
```

## Backends soportados

| Backend | Modelo | Límite | Requiere internet |
|---|---|---|---|
| Groq (gratis) | Llama 3.1 8B Instant | 30k TPM | Sí |
| LM Studio | Cualquier modelo local | Sin límite | No |

---

## Licencia

MIT — Basado en el ecosistema [CrewAI](https://github.com/crewAIInc/crewAI) (MIT License).

---

## 🤝 Contribuciones

¡Contribuciones, issues y sugerencias son bienvenidas!  
No dudes en abrir un issue o un pull request.

---

## 📬 Contacto

Para dudas o sugerencias, abre un issue o contacta a través de [Skorpion02](https://github.com/Skorpion02).

---

⭐️ **Si te gustó este proyecto, ¡déjale una estrella!**

---

<div align="center">
  <b>Hecho con ❤️ por Skorpion02</b>
</div>
