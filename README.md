# Estructuras HA — Toolbar pyRevit para Hormigón Armado

Toolbar de pyRevit para automatizar tareas repetitivas del modelado y documentación de estructuras de hormigón armado en Revit, desarrollado por (https://github.com/sangrandio).

## 🎯 Objetivo

Reducir el tiempo dedicado a tareas manuales y repetitivas en el modelado de armaduras (vigas, columnas, bases), generando de forma automática:
- Modelado de armaduras (longitudinales y estribos)
- Vistas de corte, 3D, planta y elevación según el elemento
- Planillas de cómputo y cuantificación de acero

## 🚧 Estado actual

Proyecto en desarrollo activo. Progreso por elemento:

| Elemento | Armadura | Vistas | Planilla de cómputo |
|---|---|---|---|
| Vigas | ✅ | 🔄 En progreso | ✅ |
| Columnas | ⏳ Próximamente | ⏳ | ⏳ |
| Bases | ⏳ Próximamente | ⏳ | ⏳ |

## 🛠️ Requisitos

- Autodesk Revit (probado en 2022–2027)
- [pyRevit](https://github.com/pyrevitlabs/pyRevit) 6.x o superior
- Parámetros compartidos del proyecto cargados (Posición, Forma de la barra, Tipo de elemento, entre otros — ver `/docs` próximamente)

## 📦 Instalación

1. Cloná este repositorio en tu equipo:
   ```
   git clone https://github.com/sangrandio/Barra-de-Herramientas-REVIT---Estructuras-de-concreto-reforzado.git
   ```
2. Abrí pyRevit → **Settings → Extensions** y agregá la carpeta clonada como una ruta de extensión (extension search path).
3. Reiniciá Revit o hacé **Reload** desde pyRevit.

## 📌 Cómo usarlo

1. Completá el parámetro **Posición** en cada viga (ej: V101) antes de generar la armadura — esto organiza y agrupa correctamente las barras en la planilla.
2. Corré el botón **Vigas** (armadura) sobre las vigas seleccionadas.
3. Corré el botón de **Tabla de cómputo** para generar la planilla de cuantificación de acero, agrupada por viga.

## 👤 Autor

**Santiago Grandio** — Baleal Ingeniería
Estructuras de hormigón armado y automatización BIM.

## 📄 Licencia

_A definir._

---

¿Preguntas, sugerencias o encontraste un bug? Abrí un [issue](../../issues) en este repositorio.
