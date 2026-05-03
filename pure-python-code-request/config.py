"""
Configuración del Sistema de Scraping Inmobiliario Rosario
============================================================
Este módulo contiene todas las configuraciones y lista de inmobiliarias.
"""

# =============================================================================
# LISTA DE 50 INMOBILIARIAS TOP DE ROSARIO
# =============================================================================

INMOBILIARIAS = [
    {
        "nombre": "Bassini Negocios Inmobiliarios",
        "url": "https://www.bassiniinmobiliaria.com",
        "busqueda": "/propiedades/",
        "activo": True
    },
    {
        "nombre": "Dunod Propiedades",
        "url": "https://dunod.com.ar",
        "busqueda": "/inmuebles/?status%5B%5D=venta",
        "activo": True
    },
    {
        "nombre": "Diego Ferreyra Bienes Raíces",
        "url": "https://www.diegoferreyra.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Guillermo Rodríguez Inmobiliaria",
        "url": "https://www.guillermorodriguez.com.ar",
        "busqueda": "/propiedades-venta",
        "activo": True
    },
    {
        "nombre": "Fiorina Propiedades",
        "url": "https://www.fiorinapropiedades.com.ar",
        "busqueda": "/properties-search/?status%5B%5D=venta",
        "activo": True
    },
    {
        "nombre": "Futura Negocios Inmobiliarios",
        "url": "https://www.futura-inmobiliaria.com",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Gardiol Propiedades",
        "url": "https://www.gardiolpropiedades.com",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Gimeno Propiedades",
        "url": "https://www.gimenopropiedades.com",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Gonzalo Guiñazú",
        "url": "https://www.gonzaloguinazu.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Grupo ISA",
        "url": "https://www.grupoisa.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Haus Propiedades",
        "url": "https://www.hausprop.com",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Imova Propiedades",
        "url": "https://www.imova.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Imperia Propiedades",
        "url": "https://www.imperiapropiedades.com",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Ing. Massoud Servicios Inmobiliarios",
        "url": "https://www.massoud.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Inmobiliaria Manarin",
        "url": "https://www.inmobiliariamanarin.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Integra Negocios",
        "url": "https://www.integranegocios.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Jaef Inmobiliaria",
        "url": "https://www.jaefinmobiliaria.com",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Juan Rioja",
        "url": "https://www.juanrioja.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Kusmisich Propiedades",
        "url": "https://www.kusmisichpropie96.kitepropcrm.com",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "SSL certificado inválido 2026-04-21"
    },
    {
        "nombre": "Lakiatto Inmobiliaria",
        "url": "https://www.lakiatto.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Libertador Servicios Inmobiliarios",
        "url": "https://www.libertadorargentina.com",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Galindo Negocios Inmobiliarios",
        "url": "https://www.galindoinmobiliaria.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Gamag Propiedades",
        "url": "https://www.gamagpropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "GP Propiedades",
        "url": "https://www.gppropiedades.com",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Graf Propiedades",
        "url": "https://www.grafpropiedades.com",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Ideal Propiedades",
        "url": "https://www.idealpropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Next Inmobiliaria",
        "url": "https://nextinmobiliaria.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Fuzion Inmobiliaria Boutique",
        "url": "https://www.fuzionprop.com",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Flias Propiedades",
        "url": "https://www.fliapropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Gabriela G Propiedades",
        "url": "https://www.gabrielagpropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": True
    },
    {
        "nombre": "Galarza Negocios Inmobiliarios",
        "url": "https://www.instagram.com/galarzanegociosinmobiliarios",
        "busqueda": "",
        "activo": False,
        "nota": "Solo Instagram"
    },
    {
        "nombre": "GV Propiedades",
        "url": "https://www.instagram.com/gv_propiedadesrosario",
        "busqueda": "",
        "activo": False,
        "nota": "Solo Instagram"
    },
    {
        "nombre": "Remax Rosario",
        "url": "https://www.remax.com.ar/rosario",
        "busqueda": "/listings",
        "activo": True
    },
    {
        "nombre": "Century 21 Rosario",
        "url": "https://www.century21.com.ar",
        "busqueda": "/propiedades/rosario",
        "activo": True
    },
    {
        "nombre": "Lepore Propiedades",
        "url": "https://www.leporepropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido - es de CABA, no Rosario 2026-04-21"
    },
    {
        "nombre": "Sunchales Propiedades",
        "url": "https://www.sunchalespropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Torresi Propiedades",
        "url": "https://www.torresipropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Villalon Propiedades",
        "url": "https://www.villalonpropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Propiedades Rosario",
        "url": "https://www.propiedadesrosario.com.ar",
        "busqueda": "/ventas",
        "activo": False,
        "nota": "SSL certificado inválido 2026-04-21"
    },
    {
        "nombre": "Inmobiliaria Sur",
        "url": "https://www.inmobiliariasur.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Puerto Norte Propiedades",
        "url": "https://www.puertonortepropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Barrio Cerrado Funes",
        "url": "https://www.barriocerradofunes.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Nudo Propiedades",
        "url": "https://www.nudopropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Armony Propiedades",
        "url": "https://www.armonypropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Boetto Propiedades",
        "url": "https://www.boettopropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Cavaliere Propiedades",
        "url": "https://www.cavalierepropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Castellanos Propiedades",
        "url": "https://www.castellanospropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Bilbao Propiedades",
        "url": "https://www.bilbaopropiedades.com.ar",
        "busqueda": "/propiedades",
        "activo": False,
        "nota": "DNS fallido 2026-04-21"
    },
    {
        "nombre": "Zona Prop Rosario",
        "url": "https://www.zonaprop.com.ar",
        "busqueda": "/departamentos-venta/rosario",
        "activo": True
    },
    {
        "nombre": "Argenprop Rosario",
        "url": "https://www.argenprop.com",
        "busqueda": "/departamentos/venta/rosario",
        "activo": True
    }
]

# =============================================================================
# CARACTERÍSTICAS A EXTRAER (10 PRINCIPALES)
# =============================================================================

CARACTERISTICAS = [
    "precio",           # Precio de la propiedad
    "moneda",           # Moneda (USD, ARS)
    "tipo_propiedad",   # Casa, Departamento, PH, etc.
    "ubicacion",        # Barrio/Zona
    "direccion",        # Dirección específica
    "superficie_total", # m² totales
    "superficie_cubierta", # m² cubiertos
    "ambientes",        # Cantidad de ambientes
    "dormitorios",      # Cantidad de dormitorios
    "banos",            # Cantidad de baños
    # Características adicionales importantes
    "cocheras",         # Tiene cochera
    "amenities",        # Pileta, gimnasio, etc.
    "antiguedad",       # Años de antigüedad
    "estado",           # Estado de la propiedad
    "descripcion",      # Descripción completa
    "expensas",         # Valor de expensas
    "url_propiedad",    # URL de la propiedad
    "imagen_principal", # URL imagen principal
    "fecha_publicacion",# Fecha de publicación
    "codigo"            # Código interno inmobiliaria
]

# =============================================================================
# CONFIGURACIÓN DE SCRAPING
# =============================================================================

SCRAPING_CONFIG = {
    # Timeouts y delays
    "timeout": 30,
    "min_delay": 2,
    "max_delay": 5,
    "page_delay": 3,
    
    # Reintentos
    "max_retries": 3,
    "retry_delay": 10,
    
    # Conexión
    "max_concurrent": 5,
    
    # User agents rotativos
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
    ],
    
    # Headers adicionales
    "headers": {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    },
    
    # Selenium
    "selenium": {
        "headless": True,
        "disable_images": True,
        "window_size": (1920, 1080),
        "page_load_timeout": 60
    },
    
    # Salida
    "output_dir": "resultados",
    "json_indent": 2,
    "encoding": "utf-8"
}

# =============================================================================
# SELECTORES CSS/XPATH COMUNES PARA DIFERENTES PLATAFORMAS
# =============================================================================

SELECTORES_COMUNES = {
    # Selectores genéricos para propiedades
    "contenedor_propiedades": [
        ".item-listing-wrap",
        ".item-wrap",
        ".col-propiedad",
        ".item.col-propiedad",
        ".card",
        ".property-item",
        ".propiedad",
        ".listing-item",
        "[data-property-id]",
        ".item-propiedad",
        ".card-property",
        ".property-card",
        ".listing-card",
        ".resultado-propiedad",
        ".property",
        "article.property",
        ".grid-item"
    ],
    
    "precio": [
        ".item-price",
        ".precio",
        ".price",
        ".property-price",
        ".text-white.d-flex.align-items-end",
        "[data-price]",
        ".precio-valor",
        ".valor",
        ".listing-price",
        ".price-value"
    ],
    
    "ubicacion": [
        ".item-address",
        ".ubicacion",
        ".location",
        ".property-location",
        ".barrio",
        ".direccion",
        ".address",
        "[data-location]"
    ],
    
    "superficie": [
        ".item-amenities",
        ".superficie",
        ".surface",
        ".m2",
        ".metros",
        ".text-normal",
        "[data-surface]",
        ".area"
    ],
    
    "ambientes": [
        ".ambientes",
        ".rooms",
        ".room-count",
        "[data-rooms]",
        ".dormitorios"
    ],
    
    "descripcion": [
        ".descripcion",
        ".description",
        ".property-description",
        ".detalle",
        "p.description"
    ],
    
    "titulo": [
        "h1.title",
        "h2.title",
        ".property-title",
        ".titulo-propiedad",
        "h1",
        "h2"
    ],
    
    "imagen": [
        "img.property-image",
        ".property-image img",
        ".imagen-principal img",
        "img.main-image",
        "picture img"
    ],
    
    "link": [
        "a.property-link",
        "a[href*='propiedad']",
        ".ver-mas",
        "a.ver-detalle",
        "a[href*='detalle']"
    ]
}

# =============================================================================
# PATRONES REGEX PARA EXTRACCIÓN DE DATOS
# =============================================================================

import re

PATRONES_REGEX = {
    "precio": [
        r'(?:USD|U\$S|usd)\s*[\d.,]+',
        r'[\d.,]+\s*(?:USD|U\$S|dólares?)',
        r'\$\s*[\d.,]+',
        r'(?:precio|valor)[:\s]*[\d.,]+'
    ],
    
    "superficie": [
        r'(\d+(?:[.,]\d+)?)\s*m²',
        r'(\d+(?:[.,]\d+)?)\s*metros?\s*(?:cuadrados?|²)',
        r'superficie[:\s]*(\d+(?:[.,]\d+)?)',
        r'(\d+(?:[.,]\d+)?)\s*m2'
    ],
    
    "ambientes": [
        r'(\d+)\s*(?:ambientes?|amb\.?)',
        r'(?:monoambiente|mono)',
        r'(\d+)\s*(?:dormitorios?|dorm\.?)',
        r'(\d+)\s*(?:habitaciones?|hab\.?)'
    ],
    
    "banos": [
        r'(\d+)\s*(?:baños?|bañ\.?)',
        r'(\d+)\s*(?:baños? completos?)',
        r'(?:baño|toilette)[:\s]*(\d+)'
    ],
    
    "cochera": [
        r'(\d+)\s*cocheras?',
        r'tiene\s*cochera',
        r'con\s*cochera',
        r'cochera\s*(?:incluida|disponible)'
    ],
    
    "antiguedad": [
        r'(\d+)\s*años?\s*(?:de\s*)?(?:antigüedad|antiguedad)',
        r'(?:antigüedad|antiguedad)[:\s]*(\d+)',
        r'(?:a estrenar|nuevo|0 años)'
    ],
    
    "expensas": [
        r'expensas?[:\s]*[\$]?\s*[\d.,]+',
        r'(\d+(?:[.,]\d+)?)\s*(?:de\s*)?expensas?'
    ],
    
    "moneda": [
        r'(USD|U\$S|dólares?|\$|ARS|pesos?)'
    ]
}

# =============================================================================
# CONFIGURACIÓN DE PROXIES (OPCIONAL)
# =============================================================================

PROXY_CONFIG = {
    "enabled": False,
    "proxy_list": [
        # Agregar proxies aquí si es necesario
        # "http://user:pass@proxy:port",
    ],
    "rotate_proxies": True,
    "test_proxies": True
}

# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================

LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "scraping_inmobiliario.log",
    "console": True
}


# Añadidas dinámicamente desde inmobiliarias_extra
from inmobiliarias_extra import INMOBILIARIAS_EXTRA
INMOBILIARIAS.extend(INMOBILIARIAS_EXTRA)
