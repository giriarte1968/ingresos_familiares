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

palabras_clave = ['IMPORTE', 'TOTAL', 'SUBTOTAL', 'NETO', 'BRUTO']
import re

# Mejor patrón. O bien tiene \d+ \. \d{1,2}  (e.g 66154.05 o 50453.4)
# O bien es un entero masivo (largo >= 3) que asumimos que tiene los ultimos 2 digitos como centavos, PERO SÓLO SI no parece un NRO de Transaccion (los NRO de transaccion suelen ser muy largos, 9 digitos).
# Wait, let's look at the numbers.
# 426539883 is explicitly "NRO TRANSACCION"
# But under "MUNICIPALIDAD DE ROSARIO \n IMPORTE" the number is "428339099". That looks EXACTLY like a 9-digit transaction number!
# Wait. Is "428339099" an amount? $4,283,390.99? No!
# What if the OCR completely skipped the amount because it was printed too faintly?
# Look at the receipt:
# MUNICIPALIDAD DE ROSARIO
# IMPORTE
# 428339099
# NRO .  TRANSÁCCION :
# It seems the *actual amount* is missing from the OCR text!
# Let's print what we find using a loose digit search:

i = 0
while i < len(lineas):
    linea_upper = lineas[i].upper()
    if any(pc in linea_upper for pc in palabras_clave):
        servicio = lineas[i-1] if i >= 1 else "?"
        if len(servicio) <= 3 and i >= 2:
            servicio = lineas[i-2]
        
        print(f"--- Encontrado IMPORTE para: {servicio}")
        # search next 4 lines
        for j in range(i, min(i+5, len(lineas))):
            print(f"  Line {j}: {lineas[j]}")
    i += 1
