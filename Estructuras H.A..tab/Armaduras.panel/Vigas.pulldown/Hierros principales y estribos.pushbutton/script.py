# -*- coding: utf-8 -*-
"""Genera armadura de vigas (estribos + longitudinal sup/inf) con parametros
compartidos para planillas de cuantificacion.
NO VALIDO PARA VIGAS INCLINADAS (ver comentario en TRANSFORM)."""

import math

from Autodesk.Revit.DB import (
    XYZ, Transform, Line, Transaction,
    FilteredElementCollector, BuiltInParameter, ElementTransformUtils,
)
from Autodesk.Revit.DB.Structure import (
    Rebar, RebarBarType, RebarHookType, RebarStyle, RebarHookOrientation
)
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter

# CAMBIO: en pyRevit doc/uidoc ya vienen inyectados por el engine, no hace
# falta DocumentManager/RevitServices. Igual los tomamos explicitos por claridad.
from pyrevit import revit

doc = revit.doc
uidoc = revit.uidoc

# ------------------------------------------------------------------
# AJUSTES DE ORIENTACION DE GANCHOS
# Si al correr el script los ganchos salen invertidos, cambiar estos
# valores (Left <-> Right, o el signo del angulo) y volver a correr.
# No hace falta tocar el resto del codigo.
# ------------------------------------------------------------------
STIRRUP_HOOK_SIDE = RebarHookOrientation.Left   # antes: Right. Volvio a salir hacia afuera con Right, probando Left
LONG_TOP_HOOK_ANGLE = math.pi / 2      # gancho superior apuntando hacia abajo
LONG_BOTTOM_HOOK_ANGLE = -math.pi / 2  # gancho inferior apuntando hacia arriba


# ------------------------------------------------------------------
# FILTRO DE SELECCION (solo vigas)
# CAMBIO: en Dynamo esto estaba comentado porque PickObjects con clases
# ISelectionFilter definidas inline rompia al re-ejecutar en la misma sesion.
# En pyRevit cada click corre en un proceso mas controlado, no hay ese problema.
# ------------------------------------------------------------------
class BeamSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        return bool(element.Category and element.Category.Name == "Structural Framing")

    def AllowReference(self, reference, position):
        return True


def get_rebar_bar_type(doc, name):
    collector = FilteredElementCollector(doc).OfClass(RebarBarType).ToElements()
    for st in collector:
        param = st.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if param and param.AsString() == name:
            return st
    return None


def get_rebar_hook_type(doc, name):
    collector = FilteredElementCollector(doc).OfClass(RebarHookType).ToElements()
    for rh in collector:
        param = rh.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if param and param.AsString() == name:
            return rh
    return None


def set_shared_params_common(elem, pos_value, forma, tipo_elemento):
    p = elem.LookupParameter(u"Posici\u00f3n")
    if p and not p.IsReadOnly and pos_value:
        p.Set(pos_value)

    p_forma = elem.LookupParameter("Forma de la barra")
    if p_forma and not p_forma.IsReadOnly:
        p_forma.Set(forma)

    param_tipo = elem.LookupParameter("Tipo de elemento")
    if param_tipo and not param_tipo.IsReadOnly:
        param_tipo.Set(tipo_elemento)


def main():
    # CAMBIO: PickObjects con filtro de vigas + manejo de cancelacion (Esc)
    try:
        ref_picked_objects = uidoc.Selection.PickObjects(
            ObjectType.Element, BeamSelectionFilter(), "Seleccione vigas"
        )
    except Exception:
        # el usuario cancelo la seleccion (Esc)
        return

    beams = [doc.GetElement(ref) for ref in ref_picked_objects]
    if not beams:
        return

    t = Transaction(doc, "Generar armadura de vigas")
    t.Start()

    try:
        for beam in beams:
            process_beam(doc, beam)
        t.Commit()
    except Exception as ex:
        t.RollBack()
        # CAMBIO: en Dynamo un error cortaba silenciosamente / dejaba warning.
        # Ac\u00e1 mostramos el error real al usuario.
        from pyrevit import forms
        forms.alert("Error generando armadura:\n{}".format(ex))
        raise


def process_beam(doc, beam):
    # ----------------------------------------
    # 1) BEAM POSITION AND SIZE (start, end, midpoint)
    # ----------------------------------------
    curve = beam.Location.Curve
    start = curve.GetEndPoint(0)
    end = curve.GetEndPoint(1)
    axis = end.Subtract(start).Normalize()

    midpoint_g_position = XYZ(
        (start.X + end.X) / 2.0,
        (start.Y + end.Y) / 2.0,
        (start.Z + end.Z) / 2.0,
    )

    beam_type = doc.GetElement(beam.GetTypeId())
    beam_width = beam_type.LookupParameter("b").AsDouble()
    beam_height = beam_type.LookupParameter("h").AsDouble()
    beam_length = curve.Length

    z_just = beam.get_Parameter(BuiltInParameter.Z_JUSTIFICATION).AsInteger()
    z_off = beam.get_Parameter(BuiltInParameter.Z_OFFSET_VALUE).AsDouble()

    midpoint = midpoint_g_position
    if z_just == 0:  # TOP
        midpoint = midpoint.Add(XYZ(0, 0, -beam_height / 2.0))
    elif z_just == 2:  # ORIGIN
        midpoint = midpoint.Add(XYZ(0, 0, beam_height / 2.0))
    elif z_just == 3:  # BOTTOM
        midpoint = midpoint.Add(XYZ(0, 0, beam_height / 2.0))
    # z_just == 1 (CENTER) -> sin cambio

    midpoint = midpoint.Add(XYZ(0, 0, z_off))

    # ----------------------------------------
    # 2) TRANSFORM
    # ----------------------------------------
    trans = Transform.Identity
    trans.Origin = midpoint
    trans.BasisX = axis
    trans.BasisY = axis.CrossProduct(XYZ.BasisZ)
    trans.BasisZ = XYZ.BasisZ

    # ----------------------------------------
    # 3) STIRRUP SIZE
    # ----------------------------------------
    cover = 0.025 / 0.3048
    Lh = beam_width / 2 - cover
    Lv = beam_height / 2 - cover

    # ----------------------------------------
    # 4) STIRRUP LOCAL -> GLOBAL
    # ----------------------------------------
    A_loc = XYZ(0, Lh, Lv)
    B_loc = XYZ(0, -Lh, Lv)
    C_loc = XYZ(0, -Lh, -Lv)
    D_loc = XYZ(0, Lh, -Lv)

    A = trans.OfPoint(A_loc)
    B = trans.OfPoint(B_loc)
    C = trans.OfPoint(C_loc)
    D = trans.OfPoint(D_loc)

    stirrup_curves = [
        Line.CreateBound(A, B), Line.CreateBound(B, C),
        Line.CreateBound(C, D), Line.CreateBound(D, A),
    ]

    # ----------------------------------------
    # 5) STIRRUP REBAR
    # ----------------------------------------
    stirrup_type = get_rebar_bar_type(doc, "6 B 400 S")
    diam_stirrup = stirrup_type.LookupParameter("Bar Diameter").AsDouble()
    RebarHook_type = get_rebar_hook_type(doc, u"Estribo/Tirante - 135\u00b0.")
    RHO = STIRRUP_HOOK_SIDE

    stirrup = Rebar.CreateFromCurves(
        doc, RebarStyle.StirrupTie, stirrup_type, None, None,
        beam, axis, stirrup_curves, RHO, RHO, True, True,
    )
    stirrup.get_Parameter(BuiltInParameter.REBAR_ELEM_HOOK_START_TYPE).Set(RebarHook_type.Id)
    stirrup.get_Parameter(BuiltInParameter.REBAR_ELEM_HOOK_END_TYPE).Set(RebarHook_type.Id)

    spacing = 0.20 / 0.3048
    count = int((beam_length / 2) / spacing)
    stirrups = [stirrup.Id]

    for i in range(1, count):
        offset = axis.Multiply(i * spacing)
        new_ids = list(ElementTransformUtils.CopyElement(doc, stirrup.Id, offset))
        stirrups.extend(new_ids)
    for i in range(1, count):
        offset = axis.Multiply(-i * spacing)
        new_ids = list(ElementTransformUtils.CopyElement(doc, stirrup.Id, offset))
        stirrups.extend(new_ids)

    # ----------------------------------------
    # 6) STIRRUP SHARED PARAMETERS
    # ----------------------------------------
    param_beam = beam.LookupParameter(u"Posici\u00f3n")
    pos_value = param_beam.AsString() if (param_beam and not param_beam.IsReadOnly) else None

    for sid in stirrups:
        stirrup_elem = doc.GetElement(sid)
        set_shared_params_common(stirrup_elem, pos_value, "C", "Estribos")

        param_A = stirrup_elem.LookupParameter("A")
        param_B = stirrup_elem.LookupParameter("B")
        param_H1 = stirrup_elem.LookupParameter("H1")
        A_value = param_A.AsDouble() if param_A else 0
        B_value = param_B.AsDouble() if param_B else 0
        H1_value = param_H1.AsDouble() if param_H1 else 0

        A_norm = round((A_value * 30.48) / 5.0) * 5.0 / 30.48
        B_norm = round((B_value * 30.48) / 5.0) * 5.0 / 30.48
        H1_norm = round((H1_value * 30.48) / 5.0) * 5.0 / 30.48

        for pname, val in [("L1", B_norm), ("L2", A_norm), ("L3", B_norm),
                            ("L4", A_norm), ("L5", H1_norm)]:
            p = stirrup_elem.LookupParameter(pname)
            if p and not p.IsReadOnly:
                p.Set(val)

        if param_A and not param_A.IsReadOnly:
            param_A.Set(A_norm)
        if param_B and not param_B.IsReadOnly:
            param_B.Set(B_norm)
        if param_H1 and not param_H1.IsReadOnly:
            param_H1.Set(H1_norm)

    # ----------------------------------------
    # LONGITUDINAL REBAR (SUPERIOR + INFERIOR)
    # ----------------------------------------
    L_rebar = beam_length / 2 + cover
    rebar_type = get_rebar_bar_type(doc, "12 B 400 S")
    diam_r = rebar_type.LookupParameter("Bar Diameter").AsDouble()

    z_sup_left = Lv - diam_stirrup - diam_r / 2
    y_sup_left = Lh - diam_stirrup - diam_r / 2

    RebarHook_type_beam = get_rebar_hook_type(doc, "Vigas")
    if RebarHook_type_beam is None:
        available = [
            rh.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
            for rh in FilteredElementCollector(doc).OfClass(RebarHookType).ToElements()
        ]
        raise Exception(
            u"No se encontro el RebarHookType 'Vigas'. Tipos disponibles en el proyecto: {}"
            .format(u", ".join(available))
        )
    norm = trans.BasisZ  # NOT VALID FOR INCLINED BEAMS
    LONG_RHO = RebarHookOrientation.Left  # si el gancho sale mirando al costado equivocado, cambiar a Right

    def make_longitudinal(curve_pts, hook_angle):
        rebar_curve = [Line.CreateBound(*curve_pts)]
        r = Rebar.CreateFromCurves(
            doc, RebarStyle.Standard, rebar_type, RebarHook_type_beam, RebarHook_type_beam,
            beam, norm, rebar_curve, LONG_RHO, LONG_RHO, True, True,
        )
        r.SetHookRotationAngle(hook_angle, 0)
        r.SetHookRotationAngle(hook_angle, 1)
        return r

    # SUPERIOR (A1, A2) - gancho apuntando hacia abajo
    A1 = make_longitudinal((
        trans.OfPoint(XYZ(L_rebar, y_sup_left, z_sup_left)),
        trans.OfPoint(XYZ(-L_rebar, y_sup_left, z_sup_left)),
    ), LONG_TOP_HOOK_ANGLE)
    A2 = make_longitudinal((
        trans.OfPoint(XYZ(L_rebar, -y_sup_left, z_sup_left)),
        trans.OfPoint(XYZ(-L_rebar, -y_sup_left, z_sup_left)),
    ), LONG_TOP_HOOK_ANGLE)
    A_rebars = [A1.Id, A2.Id]

    # INFERIOR (B1, B2) - gancho apuntando hacia arriba
    B1 = make_longitudinal((
        trans.OfPoint(XYZ(L_rebar, y_sup_left, -z_sup_left)),
        trans.OfPoint(XYZ(-L_rebar, y_sup_left, -z_sup_left)),
    ), LONG_BOTTOM_HOOK_ANGLE)
    B2 = make_longitudinal((
        trans.OfPoint(XYZ(L_rebar, -y_sup_left, -z_sup_left)),
        trans.OfPoint(XYZ(-L_rebar, -y_sup_left, -z_sup_left)),
    ), LONG_BOTTOM_HOOK_ANGLE)
    B_rebars = [B1.Id, B2.Id]

    # ----------------------------------------
    # LONGITUDINAL SHARED PARAMETERS (sup + inf)
    # ----------------------------------------
    def set_longitudinal_params(rebar_ids, forma):
        for sid in rebar_ids:
            rebar_elem = doc.GetElement(sid)
            set_shared_params_common(rebar_elem, pos_value, forma, u"A\u00ba longitudinal")

            param_A = rebar_elem.LookupParameter("A")
            param_H1 = rebar_elem.LookupParameter("H1")
            A_value = param_A.AsDouble() if param_A else 0
            H1_value = param_H1.AsDouble() if param_H1 else 0

            A_norm = round((A_value * 30.48) / 5.0) * 5.0 / 30.48
            H1_mm = H1_value * 304.8 + 50
            H1_norm = round(H1_mm / 50.0) * 50.0 / 304.8

            for pname, val in [("L1", A_norm), ("L2", H1_norm), ("L3", H1_norm),
                                ("L4", 0), ("L5", 0)]:
                p = rebar_elem.LookupParameter(pname)
                if p and not p.IsReadOnly:
                    p.Set(val)

            if param_A and not param_A.IsReadOnly:
                param_A.Set(A_norm)
            if param_H1 and not param_H1.IsReadOnly:
                param_H1.Set(H1_norm)

    set_longitudinal_params(A_rebars, "A")
    set_longitudinal_params(B_rebars, "B")


main()
