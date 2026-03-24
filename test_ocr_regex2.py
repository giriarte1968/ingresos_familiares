import re

raw_text = """
SANTA FE SERVICIOS
~ PAGo DE SERVICIOS
FORMA DE PAGO:
UR
S87ERO2134
TERM
86982
CUPON
070311185611
NRO
REF_
39
ID :
368
FECHA : 07/03/26
HORA : 11;25;
MoviSTAR
IMPORTE
8
66154.05
NRO
TRANSACCION 
426539883
ADI
TReoR Finsaccion;
$
420889681
MUNICIPALIDAD DE ROSARIO
IMPORTE
428339099
NRO .  TRANSÁCCION :
AGUAS SANTAFESINAS SA SIN CompRoBANTE
IMPORTE
9
50453.4/
NRO
TRÁNSACCTON :
426539895
12
aisaccion:  .85 ;
EPE
IMPORTE:
$
422349853
NRO
TRANSACCION :
PERSONAL
IMPORTE
$
' 428398509
70
NRo .
TRANSACCTON
iro ' 71aMSacclon:  38689#
CARGO POR SERVICIO
IMPORTE
60
NRO
TRANSACCION :
426540067
"""

lineas = [l.strip() for l in raw_text.split('\n') if l.strip()]

def probar_parser(lineas):
    palabras_clave = ['IMPORTE', 'TOTAL', 'SUBTOTAL', 'NETO', 'BRUTO']
    sub_pagos = []
    
    i = 0
    while i < len(lineas):
        linea_upper = lineas[i].upper()
        
        if any(pc in linea_upper for pc in palabras_clave):
            # Encontramos la palabra clave
            servicio_nombre = lineas[i-1] if i >= 1 else "Servicio Desconocido"
            if len(servicio_nombre) <= 4 and i >= 2:  # si es basura muy corta
                servicio_nombre = lineas[i-2]
            if "aisaccion" in servicio_nombre.lower() and i >= 3:
                servicio_nombre = lineas[i-3]
                
            monto_encontrado = None
            
            # Buscamos en las siguientes 5 lineas
            for j in range(i, min(i + 6, len(lineas))):
                candidato = lineas[j].replace(" ", "")
                # removemos signos extraños al principio o final
                candidato = re.sub(r'^[^\d]+', '', candidato)
                candidato = re.sub(r'[^\d]+$', '', candidato)
                candidato = candidato.replace(",", ".")
                
                if not candidato: 
                    continue
                
                # si es un numero identificador de transaccion (9+ digitos y arranca con 42)
                if len(candidato) >= 8 and candidato.startswith('42'):
                    continue
                    
                # validar que sea convertible a float
                try:
                    val = float(candidato)
                    # Excluir años como 2026, numeritos como 8, 9, 12.
                    if val >= 10 and val != 2026: 
                        monto_encontrado = val
                        # if it has a decimal point or not, we take it as is. 
                        # We can verify it's not a garbage token. 
                        # '70' is valid. '60' is valid.
                        break
                except ValueError:
                    pass
            
            if monto_encontrado:
                sub_pagos.append({
                    'descripcion': servicio_nombre,
                    'monto': monto_encontrado
                })
                i += 3 # skip forwards to not parse the same or overlap
                
        i += 1
    return sub_pagos

print(probar_parser(lineas))
