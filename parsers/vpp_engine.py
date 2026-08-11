"""
VPP Engine - Módulo de valuación de propiedades con ponderaciones
"""


def calcular_m2_equiv(prop):
    """Calcula m2 equivalentes con ponderaciones"""
    m2 = 0
    
    m2 += prop.get("m2_cubiertos", 0) * 1.0
    m2 += prop.get("m2_semicubiertos", 0) * 0.5
    m2 += prop.get("m2_descubiertos", 0) * 0.3
    m2 += prop.get("m2_comunes", 0) * 0.2
    
    return m2


def factor_piso(prop):
    """Factor según piso del edificio"""
    piso = prop.get("piso", 0)
    
    if piso == 0:
        return 0.90  # planta baja penaliza
    elif piso <= 3:
        return 1.00
    elif piso <= 7:
        return 1.03
    else:
        return 1.05


def factor_orientacion(prop):
    """Factor según orientación"""
    orientacion = prop.get("orientacion", "").lower()
    
    if orientacion in ["norte", "este"]:
        return 1.03
    elif orientacion == "sur":
        return 0.97
    else:
        return 1.00


def factor_estado(prop):
    """Factor según estado detallado"""
    estado = prop.get("estado_detalle", "bueno").lower()
    
    if estado == "excelente":
        return 1.06
    elif estado == "muy bueno":
        return 1.04
    elif estado == "regular":
        return 0.92
    else:
        return 1.00


def factor_edificio(prop):
    """Factor según calidad del edificio"""
    calidad = prop.get("calidad_edificio", "media").lower()
    
    if calidad == "premium" or calidad == "alta":
        return 1.05
    elif calidad == "economica" or calidad == "baja":
        return 0.95
    else:
        return 1.00


def factor_exteriores(prop):
    """Factor según espacios exteriores"""
    exteriores = prop.get("espacios_exteriores", [])
    
    f = 1.0
    
    if "balcon" in exteriores:
        f += 0.04
        if prop.get("balcon_techado", False):
            f += 0.03
        if prop.get("balcon_con_rejas", False):
            f -= 0.02  # penaliza estética
    
    if "patio" in exteriores:
        f += 0.03
    
    if "terraza" in exteriores:
        f += 0.05
    
    return f


def factor_ventilacion(prop):
    """Factor según tipo de ventilación"""
    ventilacion = prop.get("ventilacion", "simple").lower()
    
    if ventilacion == "cruzada":
        return 1.05
    else:
        return 1.00


def factor_terminaciones(prop):
    """Factor según terminaciones de suelo (máximo entre tipos seleccionados)"""
    terminaciones = prop.get("terminaciones_suelo", "estandar").lower()
    tipos = [t.strip() for t in terminaciones.split(",") if t.strip()]
    
    factor = 0.95
    for t in tipos:
        if "madera" in t:
            factor = max(factor, 1.04)
        elif "porcelanato" in t:
            factor = max(factor, 1.02)
        elif "ceramico" in t:
            factor = max(factor, 1.00)
    return factor


def calcular_valor_vpp(prop, m2_base_zona):
    """Calcula el valor de la propiedad usando VPP"""
    m2_equiv = calcular_m2_equiv(prop)
    
    f_total = (
        factor_piso(prop)
        * factor_orientacion(prop)
        * factor_estado(prop)
        * factor_edificio(prop)
        * factor_exteriores(prop)
        * factor_ventilacion(prop)
        * factor_terminaciones(prop)
    )
    
    valor = m2_equiv * m2_base_zona * f_total
    
    return {
        "valor": valor,
        "m2_equiv": m2_equiv,
        "factor_total": f_total,
        "factores": {
            "piso": factor_piso(prop),
            "orientacion": factor_orientacion(prop),
            "estado": factor_estado(prop),
            "edificio": factor_edificio(prop),
            "exteriores": factor_exteriores(prop),
            "ventilacion": factor_ventilacion(prop),
            "terminaciones": factor_terminaciones(prop)
        }
    }


def sanity_check(prop):
    """Verifica consistencia de datos de la propiedad"""
    errors = []
    
    # Planta baja no debería tener balcón
    if prop.get("piso") == 0 and "balcon" in prop.get("espacios_exteriores", []):
        errors.append("Planta baja con balcón - revisar")
    
    # Si no hay balcón, semicubiertos debería ser 0
    if "balcon" not in prop.get("espacios_exteriores", []) and prop.get("m2_semicubiertos", 0) > 0:
        errors.append("Sin balcón pero con m2_semicubiertos > 0")
    
    # m2_cubiertos no puede ser 0
    if prop.get("m2_cubiertos", 0) == 0:
        errors.append("m2_cubiertos es 0")
    
    return errors