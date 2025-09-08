import psutil
import time
import socket
import subprocess
import platform
import threading
import re
import requests
import os

# -- Bibliotecas específicas do Windows --
try:
    import wmi
    # win32evtlog não será usado para simplificar
except ImportError:
    print("ERRO: A biblioteca 'wmi' não foi encontrada. Instale com 'pip install wmi'.")
    exit()

# -- Bibliotecas para GPU NVIDIA (compatível com Windows) --
try:
    from pynvml import *
    import pynvml
    import GPUtil
except ImportError:
    pynvml = None
    GPUtil = None
    
# Dicionário de métricas
metrics = {
    "time": None,
    "cpu_temperature": None,
    "cpu_usage": None,
    "ram_usage": None,
    "swap_usage": None,
    "disk_usage": {},
    "cpu_frequency": None,
    "fan_rpm_cpu": None,
    "fan_rpm_gpu": None,
    "gpu_temperature": None,
    "gpu_usage": None,
    "gpu_voltage": None,
    "gpu_memory": None,
    "os_patches": None,
    "smart_overall": None,
    "ssd_perc_lifetime": None,
    "ssd_power_hours": None,
    "ssd_unsafe_shutdowns": None,
    "ssd_irrecuperable_errors": None,
    "ssd_log_errors": None,
    "battery_health": None,
    "battery_time": None,
    "battery_perc": None,
    "is_charging": None,
    "uptime": None,
    "instant_power_consumption": None,
    "click_rate": None,
    "keypress_rate": None,
    "mouse_activity": None,
    "host_list": None,
    "ping_list": None,
    "pkg_loss_list": None,
    "mac": None,
    "ip4": None,
    "ipv6": None,
    "failed_logins": None,
    "antivirus_status": None,
    "firewall_active": None,
    "firewall_status_info": None,
    "operation_sys": None,
    "os_version": None,
    "architecture": None,
    "processor": None,
    "host_name": None,
    "total_memory": None,
    "swap_total": None,
    "physical_nuclei": None,
    "logical_nuclei": None,
    "gpu_name": None,
    "motherboard_manuf": None,
    "motherboard_name": None,
    "motherboard_snum": None,
    "mb_is_replaceable": None,
    "mb_is_a_hosting_b": None,
    "mb_loc_chassis": None,
    "motherboard_version": None,
    "chassis_handle": None,
    "inter_gpu_name": None,
    "serial_number": None,
    "model": None,
    "hardware_config": None,
    "recent_hardware_failures": None,
    "installed_softwares": None,
    "country": None,
    "region_name": None,
    "city": None,
    "lat": None,
    "lon": None
}

# Inicializa o WMI
try:
    c = wmi.WMI()
except Exception as e:
    print(f"ERRO: Não foi possível conectar ao WMI. {e}")
    exit()

# --- FUNÇÕES AUXILIARES ---
def _parse_ping_windows(output, host):
    try:
        loss_match = re.search(r'Loss = (\d+)%', output)
        avg_match = re.search(r'Average = (\d+)ms', output)
        if loss_match and avg_match:
            return {'host': host, 'status': 'sucesso', 'perda_pacotes': int(loss_match.group(1)), 'latencia_avg': int(avg_match.group(1))}
        else:
            return {'host': host, 'status': 'sem_resposta', 'perda_pacotes': 100, 'latencia_avg': None}
    except Exception as e:
        return {'host': host, 'status': 'erro_parse', 'erro': str(e)}

def ping_network_stats(host='8.8.8.8', count=4):
    try:
        cmd = ['ping', '-n', str(count), host]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        return _parse_ping_windows(result.stdout, host)
    except subprocess.TimeoutExpired:
        return {'host': host, 'status': 'timeout', 'erro': 'Comando ping expirou', 'latencia_avg': None, 'perda_pacotes': 100}
    except Exception as e:
        return {'host': host, 'status': 'erro', 'erro': str(e), 'latencia_avg': None, 'perda_pacotes': 100}

def get_network_metrics():
    hosts_to_test = ['8.8.8.8', '1.1.1.1', 'google.com', 'github.com']
    host_list_temp = []
    ping_list_temp = []
    pkg_loss_list_temp = []
    for host in hosts_to_test:
        stats = ping_network_stats(host, count=4)
        host_list_temp.append(host)
        ping_list_temp.append(stats.get('latencia_avg'))
        pkg_loss_list_temp.append(stats.get('perda_pacotes'))
    return host_list_temp, ping_list_temp, pkg_loss_list_temp

# Funções de monitoramento de input
total_clicks = 0
total_keypresses = 0
total_mouse_movements = 0
mouse_activity = False
stop_event = threading.Event()
def on_click(x, y, button, pressed):
    global total_clicks
    if pressed:
        total_clicks += 1
def on_press(key):
    global total_keypresses
    total_keypresses += 1
def on_move(x, y):
    global total_mouse_movements, mouse_activity
    total_mouse_movements += 1
    mouse_activity = True
def measure_activity(duration=10):
    global total_clicks, total_keypresses, mouse_activity
    total_clicks = 0
    total_keypresses = 0
    total_mouse_movements = 0
    mouse_activity = False
    try:
        from pynput import mouse, keyboard
        with mouse.Listener(on_click=on_click, on_move=on_move) as mouse_listener, \
                keyboard.Listener(on_press=on_press) as keyboard_listener:
            stop_event.wait(duration)
            mouse_listener.stop()
            keyboard_listener.stop()
        metrics["click_rate"] = total_clicks / duration
        metrics["keypress_rate"] = total_keypresses / duration
        metrics["mouse_activity"] = mouse_activity
    except Exception as e:
        print(f"ERRO: Falha no monitoramento de entrada. {e}")


# --- EXECUÇÃO PRINCIPAL ---

# CPU e RAM
print("DEBUG: Uso de CPU/RAM/Swap - Init")
try:
    info_ram = psutil.virtual_memory()
    metrics["ram_usage"] = info_ram.percent / 100
    metrics["cpu_usage"] = psutil.cpu_percent(interval=1) / 100
    metrics["total_memory"] = info_ram.total
    info_swap = psutil.swap_memory()
    metrics["swap_usage"] = info_swap.percent / 100
    metrics["swap_total"] = info_swap.total
except Exception as e:
    print(f"ERRO: {e}")
print("DEBUG: Uso de CPU/RAM/Swap - End")

# Uptime
print("DEBUG: Tempo Ligado - Init")
try:
    metrics["uptime"] = time.time() - psutil.boot_time()
except Exception as e:
    print("ERRO: ", e)
print("DEBUG: Tempo Ligado - End")

# Localização
print("DEBUG: Localização - Init")
try:
    response = requests.get('http://ip-api.com/json/', timeout=5)
    dados_localizacao = response.json()
    if dados_localizacao['status'] == 'success':
        metrics["country"] = dados_localizacao['country']
        metrics["region_name"] = dados_localizacao['regionName']
        metrics["city"] = dados_localizacao['city']
        metrics["lat"] = dados_localizacao['lat']
        metrics["lon"] = dados_localizacao['lon']
except requests.exceptions.RequestException as e:
    print(f"Erro ao conectar com a API: {e}")
print("DEBUG: Localização - End")

# Endereços de Rede
print("DEBUG: Endereços - Init")
try:
    interfaces = psutil.net_if_addrs()
    for interface_name, interface_addresses in interfaces.items():
        if "Loopback" in interface_name or "Virtual" in interface_name or "Teredo" in interface_name: continue
        for addr in interface_addresses:
            if addr.family == socket.AF_INET: metrics["ip4"] = addr.address
            elif addr.family == socket.AF_INET6: metrics["ipv6"] = addr.address
            elif addr.family == psutil.AF_LINK: metrics["mac"] = addr.address
except Exception as e:
    print(f"Erro ao ler informações de rede: {e}")
print("DEBUG: Endereço - End")

# Info OS/CPU
print("DEBUG: Info OS/CPU/Memória - Init")
try:
    metrics["operation_sys"] = platform.system()
    metrics["os_version"] = platform.release()
    metrics["architecture"] = platform.machine()
    metrics["host_name"] = platform.node()
    metrics["processor"] = platform.processor()
    metrics["physical_nuclei"] = psutil.cpu_count(logical=False)
    metrics["logical_nuclei"] = psutil.cpu_count(logical=True)
    try: metrics["cpu_frequency"] = psutil.cpu_freq().current
    except AttributeError: print("Frequência da CPU não disponível.")
except Exception as e:
    print(f"ERROR: {e}")
print("DEBUG: Info OS/CPU/Memória - End")

# Ping e Latência
print("DEBUG: Perda de dados e ping - init")
hosts, pings, perdas = get_network_metrics()
if hosts:
    metrics["host_list"] = hosts
    metrics["ping_list"] = pings
    metrics["pkg_loss_list"] = perdas
else:
    print("Nenhuma métrica de rede válida foi coletada. As métricas permanecem None.")
print("DEBUG: Perca de dados e ping - End")

# Monitoramento de input
print("DEBUG: Input Monitoring - Init")
measure_activity(duration=10)
print("DEBUG: Input Monitoring - End")

# Uso de SSD/HD
print("DEBUG: Uso de SSD/HD - Init")
try:
    info_particoes = psutil.disk_partitions(all=True)
    for particao in info_particoes:
        if 'cdrom' in particao.opts or particao.fstype == '': continue
        drive_letter = particao.device.split(':')[0]
        metrics["disk_usage"][drive_letter] = psutil.disk_usage(particao.mountpoint).percent / 100
except Exception as e:
    print("ERRO: ", e)
print("DEBUG: Uso de SSD/HD - End")

# Temperatura/Ventoinhas
print("DEBUG: Temperatura/Ventoinhas - Init")
try:
    if c:
        temp_data = c.MSAcpi_ThermalZoneTemperature()
        if temp_data:
            metrics["cpu_temperature"] = (temp_data[0].CurrentTemperature / 10) - 273.15
except Exception as e:
    print(f"ERRO: Falha ao obter a temperatura da CPU via WMI. {e}")
metrics["fan_rpm_cpu"] = None
metrics["fan_rpm_gpu"] = None
print("DEBUG: Temperatura/Ventoinhas - End")

# Bateria
print("DEBUG: Bateria - Init")
try:
    info_bateria = psutil.sensors_battery()
    if info_bateria:
        metrics["battery_perc"] = info_bateria.percent
        metrics["is_charging"] = info_bateria.power_plugged
        metrics["battery_time"] = info_bateria.secsleft if not metrics["is_charging"] else float('inf')
    if c:
        for battery in c.Win32_Battery():
            metrics["battery_health"] = battery.EstimatedChargeRemaining / 100
            break
except Exception as e:
    print(f"ERRO: {e}")
print("DEBUG: Bateria - End")

# Info de Hardware via WMI
print("DEBUG: Info Hardware - Init")
try:
    if c:
        for board in c.Win32_BaseBoard():
            metrics["motherboard_manuf"] = board.Manufacturer
            metrics["motherboard_name"] = board.Product
            metrics["motherboard_version"] = board.Version
            metrics["motherboard_snum"] = board.SerialNumber
        for chassis in c.Win32_Chassis():
            metrics["serial_number"] = chassis.SerialNumber
            metrics["model"] = chassis.Model
        for adapter in c.Win32_VideoController():
            if adapter.Name and ('Intel' in adapter.Name or 'AMD Radeon' in adapter.Name):
                metrics["inter_gpu_name"] = adapter.Name
                break
except Exception as e:
    print(f"ERRO: Falha ao obter informações de hardware via WMI. {e}")
print("DEBUG: Info Hardware - End")

# Firewall e Antivírus via linha de comando/WMI
print("DEBUG: Firewall/Antivirus - Init")
try:
    result = subprocess.run(['netsh', 'advfirewall', 'show', 'allprofiles'], capture_output=True, text=True, check=True)
    output = result.stdout
    metrics["firewall_active"] = "State: ON" in output or "Estado: ATIVADO" in output
    metrics["firewall_status_info"] = output.strip()
except Exception as e:
    print(f"ERRO: Falha ao obter status do firewall. {e}")
try:
    if c:
        for p in c.Win32_Product():
            if p.Name and ('antivirus' in p.Name.lower() or 'security' in p.Name.lower()):
                metrics["antivirus_status"] = "Instalado"
                break
        else:
            metrics["antivirus_status"] = "Não encontrado"
except Exception as e:
    print(f"ERRO: Falha ao verificar antivírus. {e}")
print("DEBUG: Firewall/Antivirus - End")

# Softwares e Patches via WMI
print("DEBUG: Software/Patches - Init")
try:
    if c:
        metrics["installed_softwares"] = [p.Name for p in c.Win32_Product()]
        metrics["os_patches"] = [update.Description for update in c.Win32_QuickFixEngineering()]
except Exception as e:
    print(f"ERRO: Falha ao obter lista de softwares ou patches. {e}")
print("DEBUG: Software/Patches - End")

# Falhas de Login
print("DEBUG: Tentativas de Login - Init")
metrics["failed_logins"] = None
print("DEBUG: Tentativas de Login - End")

# GPU (NVIDIA)
print("DEBUG: GPU - Init")
marca = None
try:
    nvmlInit()
    print("DEBUG: GPU encontrada: NVIDIA")
    handle = nvmlDeviceGetHandleByIndex(0)
    gpu_name = nvmlDeviceGetName(handle)
    print(f"DEBUG: Nome da GPU: {gpu_name}")
    nvmlShutdown()
    marca = 'Nvidia'
except NVMLError as error:
    print("Não é uma GPU NVIDIA ou o driver não está instalado.")

if marca == 'Nvidia':
    print("DEBUG: Medidas de GPU (NVIDIA) - Init")
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            # Corrigido: pynvml.nvmlDeviceGetName() retorna uma string
            # e não precisa de .decode()
            metrics["gpu_name"] = pynvml.nvmlDeviceGetName(handle)
            metrics["gpu_temperature"] = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            metrics["gpu_usage"] = (mem_info.used / mem_info.total)
            metrics["gpu_memory"] = mem_info.total
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        pynvml.nvmlShutdown()
    except Exception as e:
        print(f"Erro ao obter métricas da GPU: {e}")
else:
    print("DEBUG: Nenhuma GPU NVIDIA detectada, pulando medidas específicas.")
print("DEBUG: GPU - End")


# Finalização
metrics["time"] = time.time()
print("\n--- Métricas Coletadas ---")
for key, value in metrics.items():
    if value is not None:
        print(f"{key}: {value}")
print("--- Fim da Execução ---")

"""!! Seção para enviar os dados para a API FastAPI !!""" 

# URL da API
API_URL = "http://127.0.0.1:8000/coletar-metricas/"

# IDs que identificam esta máquina e a empresa cliente
ID_DA_EMPRESA_CLIENTE = "6b7eecf2-8cd6-4f7a-82fe-71ec408a0c01"
LABEL_DA_MAQUINA = "Pc-Teste"

# Adiciona os parâmetros da URL
params = {
    "id_empresa": ID_DA_EMPRESA_CLIENTE,
    "label_maquina": LABEL_DA_MAQUINA
}

try:
    print("\nDEBUG: Enviando métricas para a API")
    # O Pydantic é inteligente e vai mapear as chaves do dicionário `metrics`
    # para os campos do modelo `MetricasPayload` automaticamente.
    response = requests.post(API_URL, params=params, json=metrics, timeout=20)
    
    # Verifica se a requisição foi bem sucedida
    response.raise_for_status() 
    
    print("Dados enviados com sucesso!")
    print("Resposta da API:", response.json())

except requests.exceptions.HTTPError as errh:
    print(f"Erro HTTP: {errh}")
    print(f"Detalhes da resposta: {errh.response.text}")
except requests.exceptions.ConnectionError as errc:
    print(f"Erro de Conexão: {errc}")
except requests.exceptions.Timeout as errt:
    print(f"Timeout na Requisição: {errt}")
except requests.exceptions.RequestException as err:
    print(f"Ocorreu um erro: {err}")