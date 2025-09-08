import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from supabase import create_client, Client
from datetime import datetime

load_dotenv() 

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or "SUA_URL" in SUPABASE_URL:
    raise Exception("As credenciais do Supabase não foram configuradas. Por favor, defina SUPABASE_URL.")
if not SUPABASE_KEY or "SUA_CHAVE" in SUPABASE_KEY:
    raise Exception("As credenciais do Supabase não foram configuradas. Por favor, defina SUPABASE_KEY.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Inicialização do FastAPI 
app = FastAPI(
    title="Coletor de Dados de Máquinas",
    description="API para receber e armazenar métricas de máquinas."
)

# Classe Pydantic para validação do payload
class MetricasPayload(BaseModel):
    # Usando Optional para todos no caso de alguns dados não serem enviados
    time: float
    serial_number: Optional[str] = None 
    host_name: Optional[str] = None
    model: Optional[str] = None
    operation_sys: Optional[str] = None
    os_version: Optional[str] = None
    architecture: Optional[str] = None
    processor: Optional[str] = None
    total_memory: Optional[int] = None
    swap_total: Optional[int] = None
    physical_nuclei: Optional[int] = None
    logical_nuclei: Optional[int] = None
    gpu_name: Optional[str] = None
    inter_gpu_name: Optional[str] = None
    motherboard_manuf: Optional[str] = None
    motherboard_name: Optional[str] = None
    motherboard_snum: Optional[str] = None
    cpu_temperature: Optional[float] = None
    cpu_usage: Optional[float] = None
    ram_usage: Optional[float] = None
    swap_usage: Optional[float] = None
    disk_usage_root: Optional[float] = None
    disk_usage_home: Optional[float] = None
    disk_usage_boot: Optional[float] = None
    cpu_frequency: Optional[float] = None
    fan_rpm_cpu: Optional[int] = None
    fan_rpm_gpu: Optional[int] = None
    gpu_temperature: Optional[float] = None
    gpu_usage: Optional[float] = None
    gpu_voltage: Optional[float] = None
    gpu_memory: Optional[int] = None
    os_patches: Optional[List[str]] = None
    smart_overall: Optional[str] = None
    ssd_perc_lifetime: Optional[int] = None
    ssd_power_hours: Optional[int] = None
    ssd_unsafe_shutdowns: Optional[int] = None
    ssd_irrecuperable_errors: Optional[int] = None
    ssd_log_errors: Optional[int] = None
    battery_health: Optional[float] = None
    battery_time: Optional[float] = None
    battery_perc: Optional[float] = None
    is_charging: Optional[bool] = None
    uptime: Optional[float] = None
    click_rate: Optional[float] = None
    keypress_rate: Optional[float] = None
    mouse_activity: Optional[bool] = None
    host_list: Optional[List[str]] = None
    ping_list: Optional[List[Optional[float]]] = None
    pkg_loss_list: Optional[List[Optional[float]]] = None
    mac: Optional[str] = None
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    failed_logins: Optional[int] = None
    firewall_active: Optional[bool] = None
    firewall_status_info: Optional[str] = None
    recent_hardware_failures: Optional[int] = None
    installed_softwares: Optional[List[str]] = None
    country: Optional[str] = None
    region_name: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

# Endpoint da API
@app.post("/coletar-metricas/")
def coletar_metricas(
    payload: MetricasPayload,
    id_empresa: str,
    label_maquina: Optional[str] = None
):
    """
    Recebe um payload completo de métricas, registra a máquina se for nova,
    e armazena o payload completo na tabela de métricas.
    """
    # O número de série é essencial para identificar a máquina
    if not payload.serial_number:
        raise HTTPException(status_code=400, detail="O 'serial_number' da máquina é obrigatório e não foi encontrado.")

    try:
        # Passo 1: Procurar a máquina pelo serial_number
        response = supabase.table("maquinas").select("id").eq("serial_number", payload.serial_number).execute()
        
        id_maquina_db = None
        
        # Passo 2: Se a máquina não existir, criá-la.
        if not response.data:
            print(f"Máquina com serial {payload.serial_number} não encontrada. Criando novo registro.")
            new_machine_data, count = supabase.table("maquinas").insert({
                "id_empresa": id_empresa,
                "serial_number": payload.serial_number,
                "label_maquina": label_maquina or payload.host_name
            }).execute()
            
            if not new_machine_data[1]:
                 raise HTTPException(status_code=500, detail="Falha ao criar o registro da nova máquina.")
            
            id_maquina_db = new_machine_data[1][0]['id']
        else:
            # Se a máquina já existe, apenas pegamos seu ID
            id_maquina_db = response.data[0]['id']
            # E atualizamos a data do último contato
            supabase.table("maquinas").update({"ultimo_contato": datetime.utcnow().isoformat()}).eq("id", id_maquina_db).execute()

        # Passo 3: Preparar e inserir o payload completo na tabela de métricas
        dados_para_inserir = payload.dict()
        # Adiciona a chave estrangeira e converte o timestamp
        dados_para_inserir["id_maquina"] = id_maquina_db
        dados_para_inserir["data_coleta"] = datetime.fromtimestamp(payload.time).isoformat()
        # Remove a chave 'time' original que já foi convertida para 'data_coleta'
        del dados_para_inserir['time']
        # Remove a chave 'serial_number' pois não pertence a esta tabela
        del dados_para_inserir['serial_number']

        insert_response, count_insert = supabase.table("metricas_maquina").insert(dados_para_inserir).execute()

        if not insert_response[1]:
            raise HTTPException(status_code=500, detail=f"Falha ao inserir métricas para a máquina {id_maquina_db}.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno no servidor: {str(e)}")

    return {
        "status": "sucesso",
        "mensagem": "Métricas coletadas e armazenadas.",
        "id_maquina": id_maquina_db
    }