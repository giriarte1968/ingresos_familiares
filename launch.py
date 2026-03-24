import subprocess
import sys
import time
import socket
import os
import signal

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_port(port):
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True, capture_output=True, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if 'LISTENING' in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if f':{port}' in p and i > 0:
                        pid = parts[i + 2] if i + 2 < len(parts) else None
                        if pid and pid.isdigit():
                            print(f"Killing process {pid} on port {port}")
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                            time.sleep(1)
    except Exception as e:
        print(f"Error killing port: {e}")

def main():
    port = 8503
    max_attempts = 3
    
    for attempt in range(max_attempts):
        print(f"\n{'='*50}")
        print(f"LANZADOR DE GESTOR DE INGRESOS FAMILIARES")
        print(f"{'='*50}")
        print(f"\nIntento {attempt + 1}/{max_attempts}")
        
        if is_port_in_use(port):
            print(f"Port {port} is in use. Cleaning...")
            kill_port(port)
            time.sleep(2)
        
        if not is_port_in_use(port):
            print(f"Port {port} is free. Starting app...")
            
            app_dir = os.path.dirname(os.path.abspath(__file__))
            cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(port)]
            
            try:
                process = subprocess.Popen(
                    cmd,
                    cwd=app_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                print(f"\n{'='*50}")
                print(f"APLICACION INICIADA")
                print(f"{'='*50}")
                print(f"URL: http://localhost:{port}")
                print(f"\nPresiona Ctrl+C para detener")
                print(f"{'='*50}\n")
                
                for line in process.stdout:
                    print(line, end='')
                    if "Server started" in line or "Local URL" in line:
                        break
                
                process.wait()
                
            except KeyboardInterrupt:
                print("\nDeteniendo aplicacion...")
                process.terminate()
                break
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"Port {port} still in use, trying port {port + 2}...")
            port += 2
    
    print("\nAplicacion finalizada.")

if __name__ == "__main__":
    main()
