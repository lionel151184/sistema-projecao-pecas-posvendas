import os
import socket
import subprocess
import sys
import time
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def porta_livre(inicio=8501, fim=8520):
    for porta in range(inicio, fim + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", porta)) != 0:
                return porta
    raise RuntimeError("Nenhuma porta livre entre 8501 e 8520.")


def aguardar_servidor(porta, processo, timeout=60):
    limite = time.time() + timeout
    while time.time() < limite:
        if processo.poll() is not None:
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", porta)) == 0:
                return True
        time.sleep(0.5)
    return False


def main():
    script_path = os.path.join(BASE_DIR, "app.py")
    porta = porta_livre()
    url = f"http://localhost:{porta}"

    cmd = [
        sys.executable, "-m", "streamlit", "run", script_path,
        "--server.port", str(porta),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]

    print(f"Iniciando o sistema em {url} ...")
    processo = subprocess.Popen(cmd, cwd=BASE_DIR)

    if aguardar_servidor(porta, processo):
        webbrowser.open(url)
        print("Navegador aberto. Feche esta janela (ou Ctrl+C) para encerrar o sistema.")
    else:
        print("Nao foi possivel iniciar o servidor. Verifique as dependencias (pip install -r requirements.txt).")
        sys.exit(1)

    try:
        processo.wait()
    except KeyboardInterrupt:
        processo.terminate()


if __name__ == "__main__":
    main()