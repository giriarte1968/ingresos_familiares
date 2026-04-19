"""
Test rapido de TODOS los scrapers con timeout
Ejecutar: python test_scrapers_rapido.py
"""
import sys
import time
import threading
sys.path.insert(0, 'scripts')

results = {}

def test_scraper(name, func, timeout=15):
    def run():
        try:
            t1 = time.time()
            props = func()
            results[name] = {'props': len(props), 'time': time.time() - t1, 'status': 'OK'}
        except Exception as e:
            results[name] = {'props': 0, 'time': 0, 'status': f'ERROR: {str(e)[:30]}'}
    
    thread = threading.Thread(target=run)
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        results[name] = {'props': 0, 'time': timeout, 'status': 'TIMEOUT'}

print('='*60)
print('TEST RAPIDO DE TODOS LOS SCRAPERS (15s timeout c/u)')
print('='*60)

# === Scrapers de simulacion_vpp_enriquecida ===
print('\n--- Scrapers de simulacion_vpp_enriquecida ---')
try:
    from simulacion_vpp_enriquecida import scrapear_sabatini
    test_scraper('Sabatini', scrapear_sabatini)
except: results['Sabatini'] = {'props': 0, 'time': 0, 'status': 'NO IMPORT'}

try:
    from simulacion_vpp_enriquecida import scrapear_cassina
    test_scraper('Cassina', scrapear_cassina, timeout=20)
except: results['Cassina'] = {'props': 0, 'time': 0, 'status': 'NO IMPORT'}

try:
    from simulacion_vpp_enriquecida import scrapear_valerio_dedicado
    test_scraper('Valerio', scrapear_valerio_dedicado)
except: results['Valerio'] = {'props': 0, 'time': 0, 'status': 'NO IMPORT'}

# === Scrapers sueltos ===
print('\n--- Scrapers sueltos ---')

# Uno Propiedades
try:
    import scraper_uno
    test_scraper('Uno', scraper_uno.scrapear_uno)
except Exception as e:
    results['Uno'] = {'props': 0, 'time': 0, 'status': f'ERROR: {str(e)[:30]}'}

# Remax
try:
    import scraper_remax
    test_scraper('Remax', scraper_remax.scrapear_remax)
except Exception as e:
    results['Remax'] = {'props': 0, 'time': 0, 'status': f'ERROR: {str(e)[:30]}'}

# Bienes Rosario
try:
    import scraper_bienesrosario
    test_scraper('BienesRosario', scraper_bienesrosario.scrapear_bienesrosario)
except Exception as e:
    results['BienesRosario'] = {'props': 0, 'time': 0, 'status': f'ERROR: {str(e)[:30]}'}

# Badaloni
try:
    import scraper_badaloni
    test_scraper('Badaloni', scraper_badaloni.scrapear_badaloni)
except Exception as e:
    results['Badaloni'] = {'props': 0, 'time': 0, 'status': f'ERROR: {str(e)[:30]}'}

# RG
try:
    import scraper_rg
    test_scraper('RG', scraper_rg.scrapear_bienesrosario)
except Exception as e:
    results['RG'] = {'props': 0, 'time': 0, 'status': f'ERROR: {str(e)[:30]}'}

# Resultados
print('\n' + '='*60)
print('RESUMEN')
print('='*60)
print(f'{"Nombre":15} | {"Status":15} | {"Props":>5} | {"Tiempo":>6}')
print('-'*60)

total_time = 0
total_props = 0
funcionan = []
no_funcionan = []

for name, data in results.items():
    status = data['status']
    props = data.get('props', 0)
    t = data.get('time', 0)
    total_time += t
    total_props += props
    
    if status == 'OK' and props > 0:
        funcionan.append(name)
    else:
        no_funcionan.append(name)
    
    print(f'{name:15} | {status:15} | {props:5} | {t:6.1f}s')

print('-'*60)
print(f'TOTAL: {total_props} props en {total_time:.1f}s')
print(f'Funcionan: {funcionan}')
print(f'No funcionan: {no_funcionan}')