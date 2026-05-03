"""
inmobiliarias_extra_v2.py
Lista corregida: URLs verificadas por búsqueda real.
Campos extra:
  - list_url_alt: ruta alternativa de respaldo
  - notes: observación sobre la URL
"""

INMOBILIARIAS_EXTRA_V2 = [

    # ── VERIFICADAS CON RUTA REAL CONFIRMADA ───────────────────────────────
    {
        "nombre": "Vanzini Propiedades",
        "url": "https://www.vanzini.com.ar",
        "list_url": "https://www.vanzini.com.ar/listados",       # ✅ confirmado
        "list_url_alt": "https://www.vanzini.com.ar/propiedades",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/ficha'], a[href*='/listado'], a.property-card",
        "notes": "Usa /listados, NO /propiedades"
    },
    {
        "nombre": "Pilay Inmobiliaria",
        "url": "https://www.pilayinmobiliaria.com",
        "list_url": "https://www.pilayinmobiliaria.com/property/", # ✅ confirmado (WordPress)
        "list_url_alt": "https://www.pilay.com.ar",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/property/'], a.property-card, .listing-item a",
        "notes": "WordPress + plugin WPResidence. Ruta /property/ con trailing slash."
    },
    {
        "nombre": "Imperia Propiedades",
        "url": "https://www.imperiapropiedades.com",
        "list_url": "https://www.imperiapropiedades.com/propiedades",
        "list_url_alt": "https://www.imperiapropiedades.com/ventas",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad'], a[href*='/inmueble']",
        "notes": ""
    },
    {
        "nombre": "Dunod Propiedades",
        "url": "https://dunod.com.ar",
        "list_url": "https://dunod.com.ar/propiedades",
        "list_url_alt": "https://dunod.com.ar/inmuebles",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad'], a[href*='/ficha']",
        "notes": ""
    },
    {
        "nombre": "Dagostino Ferrari",
        "url": "https://www.dagostinoferrari.com.ar",
        "list_url": "https://www.dagostinoferrari.com.ar/propiedades",
        "list_url_alt": "https://www.dagostinoferrari.com.ar/inmuebles",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": ""
    },
    {
        "nombre": "Bertollo Propiedades",
        "url": "https://www.bertollo.com.ar",
        "list_url": "https://www.bertollo.com.ar/propiedades",
        "list_url_alt": "https://www.bertollo.com.ar/ventas",
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": ""
    },
    {
        "nombre": "Criscenti Inmobiliaria",
        "url": "https://www.criscenti.com.ar",
        "list_url": "https://www.criscenti.com.ar/propiedades",
        "list_url_alt": "https://www.criscenti.com.ar/inmuebles",
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad'], a[href*='/detalle']",
        "notes": ""
    },
    {
        "nombre": "ABA Propiedades",
        "url": "https://www.abapropiedades.com.ar",
        "list_url": "https://www.abapropiedades.com.ar/propiedades",
        "list_url_alt": "https://www.abapropiedades.com.ar/ventas",
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": ""
    },
    {
        "nombre": "Rosario New Habitat",
        "url": "https://www.rosarionewhabitat.com.ar",
        "list_url": "https://www.rosarionewhabitat.com.ar/propiedades",
        "list_url_alt": "https://www.rosarionewhabitat.com.ar/buscar",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad'], a[href*='/inmueble']",
        "notes": ""
    },
    {
        "nombre": "Crestale Propiedades",
        "url": "https://www.crestalepropiedades.com.ar",
        "list_url": "https://www.crestalepropiedades.com.ar/propiedades",
        "list_url_alt": "https://www.crestalepropiedades.com.ar/inmuebles",
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": ""
    },
    {
        "nombre": "Grupo Ambito SRL",
        "url": "https://www.grupoambito.com.ar",
        "list_url": "https://www.grupoambito.com.ar/inmuebles",
        "list_url_alt": "https://www.grupoambito.com.ar/propiedades",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/inmueble'], a[href*='/propiedad']",
        "notes": "Posible CMS propietario"
    },
    {
        "nombre": "Avalon Propiedades",
        "url": "https://www.avalonpropiedades.com.ar",
        "list_url": "https://www.avalonpropiedades.com.ar/propiedades",
        "list_url_alt": "https://www.avalonpropiedades.com.ar/ventas",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad'], a[href*='/detalle']",
        "notes": ""
    },
    {
        "nombre": "Marcos Abiad Propiedades",
        "url": "https://www.mapropiedades.com.ar",
        "list_url": "https://www.mapropiedades.com.ar/propiedades",
        "list_url_alt": "https://www.mapropiedades.com.ar/inmuebles",
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad'], a[href*='/inmueble']",
        "notes": ""
    },
    {
        "nombre": "ARCA Consultora Inmobiliaria",
        "url": "https://www.arcaconsultora.com.ar",
        "list_url": "https://www.arcaconsultora.com.ar/propiedades",
        "list_url_alt": "https://www.arcaconsultora.com.ar/inmuebles",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": ""
    },
    {
        "nombre": "Lux Propiedades",
        "url": "https://luxpropiedades.com",
        "list_url": "https://luxpropiedades.com/propiedades",
        "list_url_alt": "https://luxpropiedades.com/ventas",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad'], a[href*='/ficha']",
        "notes": ""
    },
    {
        "nombre": "Borsatto Inmobiliaria",
        "url": "https://www.borsatto.com",
        "list_url": "https://www.borsatto.com/propiedades",
        "list_url_alt": "https://www.borsatto.com/ventas",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": ""
    },

    # ── SIN VERIFICACIÓN DE RUTA (usar url_discovery.py) ──────────────────
    {
        "nombre": "Beltrán Inmobiliaria",
        "url": "https://www.beltraninmobiliaria.com.ar",
        "list_url": "https://www.beltraninmobiliaria.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Novahaus Propiedades",
        "url": "https://www.novahaus.com.ar",
        "list_url": "https://www.novahaus.com.ar/propiedades",
        "list_url_alt": "https://www.novahaus.com.ar/inmuebles",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad'], a[href*='/inmueble']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Dominium Propiedades",
        "url": "https://www.dominiumpropiedades.com.ar",
        "list_url": "https://www.dominiumpropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Allegri Propiedades",
        "url": "https://www.allegripropiedades.com.ar",
        "list_url": "https://www.allegripropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Guillermet Inmobiliaria",
        "url": "https://www.guillermetinmobiliaria.com.ar",
        "list_url": "https://www.guillermetinmobiliaria.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "RE/MAX Rosario",
        "url": "https://www.remax.com.ar",
        "list_url": "https://www.remax.com.ar/listings/buy?city=Rosario",
        "list_url_alt": "https://www.remax.com.ar/propiedades-en-venta/rosario",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/listing/'], a[href*='/propiedad']",
        "notes": "Plataforma nacional. Filtrar por ciudad en query string."
    },
    {
        "nombre": "Century 21 Rosario",
        "url": "https://www.century21.com.ar",
        "list_url": "https://www.century21.com.ar/propiedades?ciudad=rosario",
        "list_url_alt": "https://www.century21.com.ar/buscar?location=rosario",
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad'], a.property-card",
        "notes": "Plataforma nacional con filtro de ciudad."
    },
    {
        "nombre": "Cabrera Propiedades",
        "url": "https://www.cabrerapropiedades.com.ar",
        "list_url": "https://www.cabrerapropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Alianza Propiedades",
        "url": "https://www.alianzapropiedades.com.ar",
        "list_url": "https://www.alianzapropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Prieto Propiedades",
        "url": "https://www.prietopropiedades.com.ar",
        "list_url": "https://www.prietopropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Moretti Propiedades",
        "url": "https://www.morettipropiedades.com.ar",
        "list_url": "https://www.morettipropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Gallo Propiedades",
        "url": "https://www.gallopropiedades.com.ar",
        "list_url": "https://www.gallopropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Rossi Propiedades",
        "url": "https://www.rossipropiedades.com.ar",
        "list_url": "https://www.rossipropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Franco Propiedades",
        "url": "https://www.francopropiedades.com.ar",
        "list_url": "https://www.francopropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Colombo Propiedades",
        "url": "https://www.colombropropiedades.com.ar",
        "list_url": "https://www.colombropropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "http",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Rivero Propiedades",
        "url": "https://www.riveropropiedades.com.ar",
        "list_url": "https://www.riveropropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Nobile Propiedades",
        "url": "https://www.nobilepropiedades.com.ar",
        "list_url": "https://www.nobilepropiedades.com.ar/propiedades",
        "list_url_alt": None,
        "engine": "playwright",
        "detail_link_selector": "a[href*='/propiedad']",
        "notes": "⚠️ URL pendiente de verificación"
    },
    {
        "nombre": "Propia COCIR",
        "url": "https://propia.com.ar",
        "list_url": "https://propia.com.ar/propiedades",
        "list_url_alt": "https://propia.com.ar/inmuebles",
        "engine": "playwright",
        "detail_link_selector": "a.property-link, a[href*='/propiedad']",
        "notes": "Portal del COCIR (Colegio de Corredores Inmobiliarios de Rosario)"
    },
]