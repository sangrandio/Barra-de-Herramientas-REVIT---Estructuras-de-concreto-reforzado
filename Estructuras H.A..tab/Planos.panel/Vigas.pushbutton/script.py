# -*- coding: utf-8 -*-
__title__   = "Vigas"
__doc__     = """Version = 1.0
Date    = 05.15.2026
________________________________________________________________
Description:



________________________________________________________________
Last Updates:

- [05.14.2026] v1.0 Entire script. It's appear text, section and template. 
Next, we debug by parts.


________________________________________________________________
Author: Theoso"""

# ╦╔╦╗╔═╗╔═╗╦═╗╔╦╗╔═╗
# ║║║║╠═╝║ ║╠╦╝ ║ ╚═╗
# ╩╩ ╩╩  ╚═╝╩╚═ ╩ ╚═╝
#==================================================

from pyrevit import revit, DB, forms
import math

# ╦  ╦╔═╗╦═╗╦╔═╗╔╗ ╦  ╔═╗╔═╗
# ╚╗╔╝╠═╣╠╦╝║╠═╣╠╩╗║  ║╣ ╚═╗
#  ╚╝ ╩ ╩╩╚═╩╩ ╩╚═╝╩═╝╚═╝╚═╝
#==================================================

doc = revit.doc
uidoc = revit.uidoc

# ╔╦╗╔═╗╦╔╗╔
# ║║║╠═╣║║║║
# ╩ ╩╩ ╩╩╝╚╝
#==================================================

#🤖 Automate Your Boring Work Here



def to_cm(feet):
    return int(round(feet * 30.48))

# 1️⃣ SELECCIÓN
selection = revit.get_selection()
if not selection:
    selection = revit.pick_elements_by_category(DB.BuiltInCategory.OST_StructuralFraming)

beams = [b for b in selection if b.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_StructuralFraming)]

# 2️⃣ TRANSACCIÓN PRINCIPAL
with revit.Transaction("Alinear Textos y Sección"):
    
    # Buscar estilo de texto
    text_type = DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType).FirstElement()
    text_type_id = text_type.Id if text_type else DB.ElementId.InvalidElementId

    # Buscar Template
    template = next((v for v in DB.FilteredElementCollector(doc).OfClass(DB.View) if v.IsTemplate and v.Name == "Sección Vigas"), None)
    
    # Buscar Family Type para Sección
    vft_id = next((vft.Id for vft in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if vft.ViewFamily == DB.ViewFamily.Section), None)

    for beam in beams:
        curve = beam.Location.Curve
        midpoint = curve.Evaluate(0.5, True)
        direction = (curve.GetEndPoint(1) - curve.GetEndPoint(0)).Normalize()
        up = DB.XYZ.BasisZ
        right = direction.CrossProduct(up)
        
        # 3️⃣ CREAR VISTA
        trans = DB.Transform.Identity
        trans.Origin = midpoint
        trans.BasisX = right
        trans.BasisY = up
        trans.BasisZ = direction
        
        section_box = DB.BoundingBoxXYZ()
        section_box.Transform = trans
        section_box.Min = DB.XYZ(-0.8, -0.8, 0) 
        section_box.Max = DB.XYZ(0.8, 0.8, 0.1)

        new_section = DB.ViewSection.CreateSection(doc, vft_id, section_box)
        
        # Nombre y Template
        pos_viga = beam.LookupParameter("Posición").AsString() or "V-Viga"
        try: new_section.Name = "Sección " + pos_viga
        except: new_section.Name = "Sección " + pos_viga + " (" + str(new_section.Id.IntegerValue) + ")"
            
        if template:
            new_section.ViewTemplateId = template.Id

        # 4️⃣ POSICIONAMIENTO DINÁMICO (LA CLAVE)
        # Forzamos la regeneración para que el Bounding Box sea preciso
        doc.Regenerate()
        
        # Obtenemos el centro real de la viga en el espacio de la vista
        bbox = beam.get_BoundingBox(new_section)
        c_x = (bbox.Min.X + bbox.Max.X) / 2
        bottom_y = bbox.Min.Y 

        # Buscamos el estribo para los datos
        rebar_in_host = DB.FilteredElementCollector(doc, new_section.Id).OfCategory(DB.BuiltInCategory.OST_Rebar).WhereElementIsNotElementType()
        stirrup = next((rb for rb in rebar_in_host if "estribo" in (rb.LookupParameter("Comentarios") or rb.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)).AsString().lower()), None)

        if stirrup:
            # Extracción de datos
            qty = stirrup.Quantity
            p_diam = stirrup.LookupParameter("Bar Diameter") or stirrup.LookupParameter("Diámetro de barra")
            diam_mm = int(round(p_diam.AsDouble() * 304.8)) if p_diam else 6
            p_spacing = stirrup.LookupParameter("Spacing") or stirrup.LookupParameter("Espaciado")
            spacing_cm = to_cm(p_spacing.AsDouble()) if p_spacing else 20
            p_length = stirrup.LookupParameter("Bar Length") or stirrup.LookupParameter("Longitud de barra")
            l_total_cm = to_cm(p_length.AsDouble()) if p_length else 100
            
            info_obra = "{} \u00f8 {} c/{} L={} cm".format(qty, diam_mm, spacing_cm, l_total_cm)

            # --- CREACIÓN DE TEXTOS ALINEADOS AL CENTRO ---
            # Nota técnica (0.4 pies abajo de la viga)
            pos_info = DB.XYZ(c_x, bottom_y - 0.4, 0)
            text_info = DB.TextNote.Create(doc, new_section.Id, pos_info, info_obra, text_type_id)
            
            # Título Corte A-A (0.8 pies abajo de la viga)
            # Usamos un ancho fijo para que se centre bien
            pos_titulo = DB.XYZ(c_x, bottom_y - 0.8, 0)
            text_titulo = DB.TextNote.Create(doc, new_section.Id, pos_titulo, "Corte A-A", text_type_id)
            
            # Forzamos alineación central en los textos
            text_info.HorizontalAlignment = DB.HorizontalTextAlignment.Center
            text_titulo.HorizontalAlignment = DB.HorizontalTextAlignment.Center

            # 5️⃣ BENDING DETAIL (Gráfico a la derecha)
            detail_pos = DB.XYZ(bbox.Max.X + 0.6, (bbox.Min.Y + bbox.Max.Y)/2, 0)
            try:
                DB.Structure.RebarBendingDetail.Create(doc, new_section.Id, stirrup.Id, detail_pos, new_section.ViewDirection, new_section.RightDirection, new_section.UpDirection)
            except: pass

    print("Sección generada con textos centrados.")

if 'new_section' in locals():
    uidoc.ActiveView = new_section