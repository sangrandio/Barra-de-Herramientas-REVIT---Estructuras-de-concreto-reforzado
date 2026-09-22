# -*- coding: utf-8 -*-
__title__   = "Vigas"
__doc__     = """Version = 1.1
Date    = 07.09.2026
________________________________________________________________
Description:

Genera la planilla de computo Aº-vigas, agrupada por Viga y por
ID de barra (A/B/C), usando los parametros compartidos seteados
por el script de armado de vigas.

________________________________________________________________
Last Updates:

- [05.14.2026] v1.0 Select all the beams and create the main bars and the stirrup
- [07.09.2026] v1.1 CAMBIO: se reemplazo el campo nativo "Comments" por el
  parametro compartido real "Tipo de elemento" (el que llena el script de
  armado con "Estribos" / "Aº longitudinal"), que antes quedaba vacio.

________________________________________________________________
Author: Theoso"""

# ╦╔╦╗╔═╗╔═╗╦═╗╔╦╗╔═╗
# ║║║║╠═╝║ ║╠╦╝ ║ ╚═╗
# ╩╩ ╩╩  ╚═╝╩╚═ ╩ ╚═╝
#==================================================
from Autodesk.Revit.DB import *

#.NET Imports
import clr
clr.AddReference('System')
from Autodesk.Revit.UI.Selection import*
from Autodesk.Revit.DB.Structure import *
from Autodesk.Revit.UI.Selection import ISelectionFilter
from pyrevit import revit
import math

# ╦  ╦╔═╗╦═╗╦╔═╗╔╗ ╦  ╔═╗╔═╗
# ╚╗╔╝╠═╣╠╦╝║╠═╣╠╩╗║  ║╣ ╚═╗
#  ╚╝ ╩ ╩╩╚═╩╩ ╩╚═╝╩═╝╚═╝╚═╝
#==================================================

from pyrevit import revit, DB

doc = revit.doc

# ╔╦╗╔═╗╦╔╗╔
# ║║║╠═╣║║║║
# ╩ ╩╩ ╩╩╝╚╝
#==================================================

#-----------------------------------------------------------------------------------------
# 1️⃣ GENERAR PLANILLA DE CÓMPUTO Aº-vigas
#-----------------------------------------------------------------------------------------

with revit.Transaction("Crear Tabla Aº-vigas Final"):
    base_name = "Aº-vigas"
    final_name = base_name

    # 1. Nombre único
    schedules = DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule).ToElements()
    existing_names = [s.Name for s in schedules]
    counter = 1
    while final_name in existing_names:
        final_name = "{}-{}".format(base_name, counter)
        counter += 1

    # 2. Crear tabla
    cat_id = DB.ElementId(DB.BuiltInCategory.OST_Rebar)
    tabla = DB.ViewSchedule.CreateSchedule(doc, cat_id)
    tabla.Name = final_name

    definition = tabla.Definition
    schedulable_fields = definition.GetSchedulableFields()

    # 3. Mapeo de campos
    # CAMBIO: "Comments" -> "Tipo de elemento" (parametro compartido real,
    # coincide con el nombre exacto que usa el script de armado de vigas)
    mapeo_campos = [
        ("Posición", "Posición"),
        ("Bar Diameter", "Diámetro (mm)"),
        ("Tipo de elemento", "Tipo de elemento"),
        ("Quantity", "Cantidad"),
        ("Bar Length", "L (m)"),
        ("Total Bar Length", "L total (m)"),
        ("Bending Detail", "Forma de la barra"),
        ("Forma de la barra", "ID_Grupo")
    ]

    for p_name, custom_name in mapeo_campos:
        for sf in schedulable_fields:
            s_name = sf.GetName(doc)
            if s_name == p_name or (p_name == "Bending Detail" and "plegado" in s_name.lower()):
                field = definition.AddField(sf)
                field.ColumnHeading = custom_name

                # --- CONFIGURACIÓN DE UNIDADES Y TOTALES ---
                options = field.GetFormatOptions()

                # A. Si es una columna de longitud (L o L total)
                if "L (" in custom_name or "total" in custom_name.lower():
                    options.UseDefault = False # No usar unidades del proyecto
                    # Usamos ForgeTypeId para Metros (Revit 2022+)
                    try:
                        metros_id = DB.UnitTypeId.Meters
                        options.SetUnitTypeId(metros_id)
                        # Seteamos 2 decimales (0.01)
                        options.Accuracy = 0.01
                    except:
                        pass # Si falla por versión, sigue con default

                field.SetFormatOptions(options)

                # B. Forzar suma (Totals) para Cantidad y L total
                if any(x in custom_name.lower() for x in ["cantidad", "total"]):
                    try:
                        field.DisplayType = DB.ScheduleFieldDisplayType.Totals
                    except:
                        pass
                break

    # 4. AGRUPAMIENTO (Anti-error 2025)
    try:
        definition.ItemizeEveryInstance = False
    except:
        try: definition.IsItemized = False
        except: pass

    if definition.GetFieldCount() >= 2:
        # Nivel 1: Posición (Encabezado) - CAMBIO: se deja visible como 1a columna
        f_viga = definition.GetField(0)
        sort_viga = DB.ScheduleSortGroupField(f_viga.FieldId)
        sort_viga.ShowHeader = True
        sort_viga.ShowBlankLine = True
        definition.AddSortGroupField(sort_viga)

        # Nivel 2: ID_Grupo (A, B, C) -> Para que sume las barras
        for i in range(definition.GetFieldCount()):
            if definition.GetField(i).ColumnHeading == "ID_Grupo":
                f_id = definition.GetField(i)
                sort_id = DB.ScheduleSortGroupField(f_id.FieldId)
                definition.AddSortGroupField(sort_id)
                f_id.IsHidden = True
                break

    # 5. COLOR DE TÍTULO (verde Baleal #7ED956, sacado del logo)
    try:
        verde_baleal = DB.Color(126, 217, 86)
        table_data = tabla.GetTableData()
        title_section = table_data.GetSectionData(DB.SectionType.Title)
        cell_style = title_section.GetTableCellStyle(0, 0)
        override_options = cell_style.GetCellStyleOverrideOptions()
        override_options.TextColor = True
        cell_style.SetCellStyleOverrideOptions(override_options)
        cell_style.TextColor = verde_baleal
        title_section.SetTableCellStyle(0, 0, cell_style)
    except Exception as ex:
        print("No se pudo aplicar el color de titulo automaticamente: {}".format(ex))
        print("Se puede setear manualmente: click derecho en la tabla > Propiedades > "
              "Apariencia > estilo de texto del titulo, con color RGB(126,217,86) / #7ED956")

# --- EJECUCIÓN ---
try:
    revit.uidoc.ActiveView = tabla
except:
    pass

print("Tabla generada con éxito: " + final_name)
