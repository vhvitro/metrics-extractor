#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import sys

def main():
    """
    Carrega as variáveis de ambiente do arquivo .env e executa o script de extração.
    """
    # A localização deste script é .../linux/run_extraction.py
    # A raiz do projeto é a pasta pai da pasta onde este script está.
    script_location = Path(__file__).parent
    project_root = script_location.parent

    # O caminho para o .env na raiz do projeto
    env_path = project_root / ".env"

    # O caminho para o script de extração (que está na mesma pasta que este)
    extraction_script_path = script_location / "extract_linux.py"

    if not env_path.exists():
        print(f"Erro: Arquivo .env não encontrado em {project_root}")
        return

    load_dotenv(dotenv_path=env_path)

    print("Variáveis de ambiente carregadas. Executando o script de extração...")
    
    company_id = os.getenv("COMPANY_ID")
    if not company_id:
        print("Aviso: COMPANY_ID não foi encontrada nas variáveis de ambiente.")
    
    try:
        subprocess.run(
            [sys.executable, str(extraction_script_path)], 
            check=True, 
            capture_output=True, 
            text=True
        )
        print("Script de extração executado com sucesso.")
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o script de extração:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
    except FileNotFoundError:
        print(f"Erro: Script de extração não encontrado em {extraction_script_path}")

if __name__ == "__main__":
    main()