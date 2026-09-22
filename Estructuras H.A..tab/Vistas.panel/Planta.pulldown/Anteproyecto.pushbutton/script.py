# -*- coding: utf-8 -*-
__title__   = "Anteproyecto"
__doc__     = """Version = 1.0
Date    = 05.10.2026
________________________________________________________________
Description:

This is the placeholder for a .pushbutton in a /pulldown
You can use it to start your pyRevit Add-In

________________________________________________________________
How-To:

1. [Hold ALT + CLICK] on the button to open its source folder.
You will be able to override this placeholder.

2. Automate Your Boring Work ;)

________________________________________________________________
TODO:
[FEATURE] - Describe Your ToDo Tasks Here

________________________________________________________________
Last Updates:

- [05.07.2026] v1.0 Select all the structural level, generate plan view and load a structural view template
- [05.09.2026] v1.0 Select all the structural level, generate plan view and load a structural view template
- [05.10.2026] v1.0 Select all the structural level, generate plan view and load a structural view template
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
from System.Collections.Generic import List
from Autodesk.Revit.UI.Selection import*


# ╦  ╦╔═╗╦═╗╦╔═╗╔╗ ╦  ╔═╗╔═╗
# ╚╗╔╝╠═╣╠╦╝║╠═╣╠╩╗║  ║╣ ╚═╗
#  ╚╝ ╩ ╩╩╚═╩╩ ╩╚═╝╩═╝╚═╝╚═╝
#==================================================
app    = __revit__.Application
uidoc  = __revit__.ActiveUIDocument
doc    = __revit__.ActiveUIDocument.Document #type:Document
selection = uidoc.Selection                     #type: Selection

# ╔╦╗╔═╗╦╔╗╔
# ║║║╠═╣║║║║
# ╩ ╩╩ ╩╩╝╚╝
#==================================================

#🤖 Automate Your Boring Work Here

# 1️⃣ Buscar TODOS los tipos de vista de planta estructural
vt_collector = FilteredElementCollector(doc).OfClass(ViewFamilyType)

# 2️⃣ Encontrar el primero que sea de la familia "StructuralPlan"
struct_view_type = None
for vt in vt_collector:
    if vt.ViewFamily == ViewFamily.StructuralPlan:
        struct_view_type = vt
        break
    
# 3️⃣ Verificar si lo encontramos antes de imprimir o usar
if struct_view_type:
    
    #--------- DEBUG-----------
    view_name = struct_view_type.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME) 
    print("Vamo' papa, un paso más") 
    print(view_name.AsString())  
    #--------- DEBUG-----------
    
    # 4️⃣--- BUSCAR EL VIEW TEMPLATE ---
    nombre_template = "Planta-Anteproyecto" 
    view_template = None

    # Buscamos en todas las vistas del proyecto
    vistas = FilteredElementCollector(doc).OfClass(View)
    for v in vistas:
        if v.IsTemplate and v.Name == nombre_template:
            view_template = v
            view_template_name=view_template.get_Parameter(BuiltInParameter.VIEW_NAME)
            print(view_template_name.AsString())
            
            break

    if not view_template:
        print("OJO: No encontré el template '{}'. Se crearán las vistas sin él.".format(nombre_template))
    
    
    # 4️⃣ Obtain all levels
    all_levels = FilteredElementCollector(doc).OfClass(Level).ToElements() # ALL LEVELS
    
    # 5️⃣ Create a transaction
    with Transaction(doc, 'Structural Plan View') as t:
        t.Start() # <--- AHORA SÍ: Movido 4 espacios a la derecha

        # 6️⃣ create a view for all the levels
        for lvl in all_levels:
            # Creamos la vista para cada nivel recolectado         
            view_floor = ViewPlan.Create(doc, struct_view_type.Id, lvl.Id)
            
            # --- ASIGNAR EL TEMPLATE ---
            if view_template:
                view_floor.ViewTemplateId = view_template.Id
            
            #--------- DEBUG-----------
            all_levels_name=lvl.get_Parameter(BuiltInParameter.DATUM_TEXT)
            print(all_levels_name.AsString())
            #--------- DEBUG-----------

        # El Commit debe estar a la misma altura que el Start
        t.Commit() 
    
else:
    # Si no hay ninguno, avisamos para no romper el script
    print("No se encontró un ViewFamilyType de Structural Plan en este modelo.")




    
    
    
    
#==================================================

