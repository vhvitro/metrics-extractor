import psutil
import time
import socket
import subprocess
import platform
import threading
import re
import math
import requests
import os
from dotenv import load_dotenv
import hashlib
import uuid
import winreg
import datetime 
try:
    from pyJoules.energy_meter import EnergyContext
    from pyJoules.handler.csv_handler import CSVHandler
    from pyJoules.device.rapl_device import RaplPackageDomain, RaplDramDomain
except ImportError:
    print("AVISO: A biblioteca 'pyJoules' não está instalada. A coleta de potência será por estimativa.")

# -- Bibliotecas específicas do Windows --
try:
    import wmi
except ImportError:
    print("ERRO: A biblioteca 'wmi' não foi encontrada. Instale com 'pip install wmi'.")
    exit()

# -- Bibliotecas para GPU NVIDIA --
try:
    from pynvml import *
    import pynvml
except ImportError:
    pynvml = None

# --- Dicionário de Métricas (Completo) ---
metrics = {
    "time": None, "cpu_temperature": None, "cpu_usage": None, "ram_usage": None, "swap_usage": None, 
    "disk_usage": {}, "cpu_frequency": None, "fan_rpm_cpu": None, "fan_rpm_gpu": None, 
    "gpu_temperature": None, "gpu_usage": None, "gpu_voltage": None, "gpu_memory": None, 
    "os_patches": None, "smart_overall": None, "ssd_perc_lifetime": None, "ssd_power_hours": None, 
    "ssd_unsafe_shutdowns": None, "ssd_irrecuperable_errors": None, "ssd_log_errors": None, 
    "battery_health": None, "battery_time": None, "battery_perc": None, "is_charging": None, 
    "uptime": None, "instant_power_consumption": None, "click_rate": None, "keypress_rate": None, 
    "mouse_activity": None, "host_list": None, "ping_list": None, "pkg_loss_list": None, 
    "mac": None, "ipv4": None, "ipv6": None, "failed_logins": None, "antivirus_status": None, 
    "firewall_active": None, "firewall_status_info": None, "operation_sys": None, 
    "os_version": None, "architecture": None, "processor": None, "host_name": None, 
    "total_memory": None, "swap_total": None, "physical_nuclei": None, "logical_nuclei": None, 
    "gpu_name": None, "motherboard_manuf": None, "motherboard_name": None, "motherboard_snum": None, 
    "mb_is_replaceable": None, "mb_is_a_hosting_b": None, "mb_loc_chassis": None, 
    "motherboard_version": None, "chassis_handle": None, "inter_gpu_name": None, 
    "serial_number": None, "model": None, "hardware_config": None, "recent_hardware_failures": None, 
    "installed_softwares": None, "country": None, "region_name": None, "city": None, 
    "lat": None, "lon": None
}

# --- FUNÇÕES AUXILIARES ---

def gerar_identificador_unico(wmi_connection):
    print("DEBUG: Nenhum serial encontrado, gerando fingerprint da máquina...")
    try:
        cpu_id = wmi_connection.Win32_Processor()[0].ProcessorId.strip()
        board = wmi_connection.Win32_BaseBoard()[0]
        board_info = f"{board.Manufacturer.strip()}{board.Product.strip()}"
        mac_address = ""
        for interface, addrs in psutil.net_if_addrs().items():
            if "Loopback" in interface or "Virtual" in interface: continue
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    mac_address = addr.address.replace(':', ''); break
            if mac_address: break
        if not all([cpu_id, board_info, mac_address]):
            return str(uuid.uuid4())
        combined_string = f"{cpu_id}-{board_info}-{mac_address}"
        return hashlib.sha256(combined_string.encode('utf-8')).hexdigest()
    except Exception as e:
        print(f"ERRO CRÍTICO ao gerar fingerprint: {e}"); return str(uuid.uuid4())

def get_serial_number(wmi_connection):
    try:
        # 1. Tenta Win32_BIOS (geralmente o mais confiável para o serial do sistema)
        bios = wmi_connection.Win32_BIOS()[0]
        if bios.SerialNumber and len(bios.SerialNumber.strip()) > 4:
            return bios.SerialNumber.strip()

        # 2. Tenta Win32_ComputerSystemProduct (outra fonte comum para o serial do sistema)
        system_product = wmi_connection.Win32_ComputerSystemProduct()[0]
        if system_product.IdentifyingNumber and len(system_product.IdentifyingNumber.strip()) > 4:
            return system_product.IdentifyingNumber.strip()

        # 3. Tenta Win32_SystemEnclosure (serial do chassi)
        enclosure = wmi_connection.Win32_SystemEnclosure()[0]
        if enclosure.SerialNumber and len(enclosure.SerialNumber.strip()) > 4:
            return enclosure.SerialNumber.strip()

        # 4. Tenta Win32_BaseBoard (serial da placa-mãe, como último recurso antes do hash)
        board = wmi_connection.Win32_BaseBoard()[0]
        if board.SerialNumber and len(board.SerialNumber.strip()) > 4:
            return board.SerialNumber.strip()

        # 5. Se tudo falhar, gera um identificador único
        return gerar_identificador_unico(wmi_connection)

    except Exception as e:
        print(f"AVISO: Falha ao obter serial_number: {e}")
        return gerar_identificador_unico(wmi_connection)
    
def get_instant_power_consumption(metrics):
    """
    Coleta o consumo de energia instantâneo da CPU/RAM (via pyJoules/TDP) e da GPU (via NVML).
    """
    try:
        # A API do pyJoules para Windows (WMI) pode ser mais complexa
        # e o pyJoules foca muito no Linux/RAPL. Faremos a estimativa mais simples
        # e confiável baseada no uso da CPU como fallback principal,
        # e tentaremos a leitura da GPU via NVML (que é robusta no Windows).

        cpu_ram_power = 0.0
        
        # --- Estimativa de Potência da CPU (Fallback) ---
        # No Windows, a leitura de potência da CPU não é trivial sem drivers específicos (RAPL)
        # O método mais seguro é estimar via TDP * uso
        
        # Valor de TDP típico para notebook (pode ser ajustado)
        cpu_tdp = 35.0  # Watts
        cpu_usage = psutil.cpu_percent(interval=0.5) / 100.0
        cpu_ram_power = cpu_usage * cpu_tdp
        print(f"DEBUG: Potência estimada (CPU) = {cpu_ram_power:.2f} W (via TDP x uso)")

        # --- Potência da GPU (NVIDIA via pynvml) ---
        gpu_power = 0.0
        if pynvml is not None:
            try:
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                # nvmlDeviceGetPowerUsage retorna mW (miliwatts)
                gpu_power_mw = pynvml.nvmlDeviceGetPowerUsage(handle)
                gpu_power = gpu_power_mw / 1000.0  # mW → W
                pynvml.nvmlShutdown()
            except Exception as gpu_err:
                # É comum falhar se for uma GPU integrada
                # print(f"DEBUG: Falha ao obter potência da GPU via NVML: {gpu_err}")
                pass
        
        # Potência total instantânea (CPU+RAM + GPU)
        total_power = cpu_ram_power + gpu_power
        metrics["instant_power_consumption"] = round(total_power, 2)

        print(f"DEBUG: CPU+RAM: {cpu_ram_power:.2f} W | GPU: {gpu_power:.2f} W | Total: {total_power:.2f} W")

    except Exception as e:
        print(f"ERRO: Falha crítica na coleta de potência: {e}")
        metrics["instant_power_consumption"] = None

def get_integrated_gpu_name(wmi_connection):
    try:
        gpu_names = []
        for gpu in wmi_connection.Win32_VideoController():
            name = gpu.Name.strip()
            if name and "NVIDIA" not in name:
                gpu_names.append(name)
        if gpu_names:
            metrics["inter_gpu_name"] = ", ".join(gpu_names)
    except Exception as e:
        print(f"AVISO: Falha ao obter GPU integrada. {e}")

def get_network_metrics():
    hosts_to_test = ['8.8.8.8', '1.1.1.1', 'google.com']
    results = []
    for host in hosts_to_test:
        try:
            cmd = ['ping', '-n', '4', host]
            output = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW, encoding='cp850', errors='ignore'
            ).stdout

            # Tenta capturar a linha com Enviados/Recebidos/Perdidos (independente do idioma)
            # Exemplo PT-BR: "Pacotes: Enviados = 4, Recebidos = 4, Perdidos = 0 (0% de perda)"
            # Exemplo EN:    "Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)"
            line_match = re.search(r'(\d+).+?(\d+).+?(\d+).*?\(', output)
            
            perda = None
            if line_match:
                enviados = int(line_match.group(1))
                recebidos = int(line_match.group(2))
                perdidos = int(line_match.group(3))
                if enviados > 0:
                    perda = int((perdidos / enviados) * 100)

            # Latência média (PT-BR: "Média = Xms", EN: "Average = Xms")
            avg_match = re.search(r'(M[eé]dia|Average).*?=\s?(\d+)ms', output, re.IGNORECASE)
            latencia = int(avg_match.group(2)) if avg_match else None

            results.append({
                'host': host,
                'perda_pacotes': perda if perda is not None else 100,
                'latencia_avg': latencia
            })

        except subprocess.TimeoutExpired:
            results.append({'host': host, 'perda_pacotes': 100, 'latencia_avg': None})

    metrics["host_list"] = [r['host'] for r in results]
    metrics["ping_list"] = [r['latencia_avg'] for r in results]
    metrics["pkg_loss_list"] = [r['perda_pacotes'] for r in results]



def get_antivirus_status():
    try:
        wmi_security = wmi.WMI(namespace="root\\SecurityCenter2")
        av_products = wmi_security.AntiVirusProduct()
        return av_products[0].displayName if av_products else "Nenhum antivírus detectado"
    except Exception as e:
        print(f"ERRO ao verificar antivírus: {e}"); return "Falha na verificação"

def get_installed_software():
    software_list = []
    uninstall_paths = [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]
    for path in uninstall_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        sub_key_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub_key_name) as sub_key:
                            display_name = winreg.QueryValueEx(sub_key, "DisplayName")[0]
                            if display_name and "update" not in display_name.lower():
                                software_list.append(display_name)
                    except OSError:
                        continue
        except FileNotFoundError:
            pass
    return sorted(list(set(software_list)))

total_clicks, total_keypresses, mouse_activity = 0, 0, False
stop_event = threading.Event()
def on_click(x, y, button, pressed):
    global total_clicks
    if pressed: total_clicks += 1
def on_press(key):
    global total_keypresses
    total_keypresses += 1
def measure_activity(duration=10):
    global total_clicks, total_keypresses, mouse_activity
    total_clicks, total_keypresses, mouse_activity = 0, 0, False
    try:
        from pynput import mouse, keyboard
        with mouse.Listener(on_click=on_click) as m_listener, keyboard.Listener(on_press=on_press) as k_listener:
            stop_event.wait(duration)
            m_listener.stop(); k_listener.stop()
        metrics["click_rate"] = total_clicks / duration
        metrics["keypress_rate"] = total_keypresses / duration
        metrics["mouse_activity"] = total_clicks > 0 or total_keypresses > 0
    except Exception as e:
        print(f"AVISO: Falha no monitoramento de entrada ('pynput' pode não estar instalado). {e}")

def get_battery_health(wmi_connection):
    try:
        battery_info = wmi_connection.Win32_Battery()[0]
        if battery_info.DesignCapacity and battery_info.FullChargeCapacity:
            design_capacity = float(battery_info.DesignCapacity)
            full_charge_capacity = float(battery_info.FullChargeCapacity)
            if design_capacity > 0:
                health = (full_charge_capacity / design_capacity) * 100
                metrics["battery_health"] = round(health, 2)
    except Exception as e:
        print(f"AVISO: Não foi possível calcular a saúde da bateria. {e}")

def get_smart_status():
    try:
        cmd = "wmic diskdrive get status"
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        status_list = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        actual_statuses = status_list[1:]
        if not actual_statuses:
            metrics["smart_overall"] = "Not Available"
        elif any(s != "OK" for s in actual_statuses):
            metrics["smart_overall"] = "Failure_Predicted"
        else:
            metrics["smart_overall"] = "OK"
    except Exception as e:
        print(f"ERRO: Falha ao obter status S.M.A.R.T. via wmic. {e}")

def get_failed_logins(wmi_connection, hours_ago=24):
    try:
        start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
        wmi_time_str = start_time.strftime('%Y%m%d%H%M%S.000000+000')
        query = f"SELECT * FROM Win32_NTLogEvent WHERE Logfile='Security' AND EventCode='4625' AND TimeGenerated >= '{wmi_time_str}'"
        metrics["failed_logins"] = len(wmi_connection.query(query))
    except wmi.x_wmi:
        print("AVISO: Falha ao consultar logs de segurança. Execute como Administrador.")
    except Exception as e:
        print(f"ERRO ao contar falhas de login: {e}")

def get_cpu_temperature_wmi():
    try:
        w = wmi.WMI(namespace="root\\WMI")
        temp_info = w.MSAcpi_ThermalZoneTemperature()
        if temp_info:
            metrics["cpu_temperature"] = round((temp_info[0].CurrentTemperature / 10.0) - 273.15, 2)
    except Exception as e:
        print(f"ERRO ao obter temperatura via root\\WMI: {e}")

def sanitize_json_values(data):
    if isinstance(data, dict): return {k: sanitize_json_values(v) for k, v in data.items()}
    if isinstance(data, list): return [sanitize_json_values(item) for item in data]
    if isinstance(data, float) and (math.isinf(data) or math.isnan(data)): return None
    return data

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    try:
        print("DEBUG: Conectando ao WMI - Init")
        c = wmi.WMI()
        print("DEBUG: Conectado ao WMI - End")
    except Exception as e:
        print(f"ERRO CRÍTICO: Não foi possível conectar ao WMI. {e}")
        exit()

    print("--- Iniciando Coleta de Métricas ---")

    print("DEBUG: Coletando métricas básicas de CPU/RAM/Uptime - Init")
    metrics.update({
        "ram_usage": psutil.virtual_memory().percent / 100,
        "cpu_usage": psutil.cpu_percent(interval=1),
        "total_memory": psutil.virtual_memory().total,
        "swap_usage": psutil.swap_memory().percent,
        "swap_total": psutil.swap_memory().total,
        "uptime": time.time() - psutil.boot_time()
    })
    print("DEBUG: Coletando métricas básicas de CPU/RAM/Uptime - End")

    print("DEBUG: Chamando get_network_metrics() - Init")
    get_network_metrics()
    print("DEBUG: Chamando get_network_metrics() - End")

    try:
        resp = requests.get('http://ip-api.com/json/', timeout=5).json()
        if resp.get('status') == 'success':
            metrics.update({
                k: resp.get(v) for k, v in {
                    "country": "country",
                    "region_name": "regionName",
                    "city": "city",
                    "lat": "lat",
                    "lon": "lon"
                }.items()
            })
            print(f"DEBUG: Localização obtida: {metrics.get('country')}, {metrics.get('city')}")
    except Exception as e:
        print(f"DEBUG: Falha ao obter localização: {e}")

    print("DEBUG: Coletando endereços de rede (MAC/IP) - Init")
    try:
        stats = psutil.net_if_stats()
        all_addrs = psutil.net_if_addrs()
        for interface, addr_list in all_addrs.items():
            if interface in stats and stats[interface].isup and "Loopback" not in interface:
                for addr in addr_list:
                    if addr.family == psutil.AF_LINK and not metrics.get("mac"):
                        metrics["mac"] = addr.address
                    elif addr.family == socket.AF_INET and not metrics.get("ip4"):
                        metrics["ipv4"] = addr.address
                    elif addr.family == socket.AF_INET6 and not metrics.get("ipv6"):
                        metrics["ipv6"] = addr.address
    except Exception as e:
        print(f"AVISO: Falha ao obter endereços de rede: {e}")
    print("DEBUG: Coletando endereços de rede (MAC/IP) - End")

    print("DEBUG: Monitorando atividade de entrada (10s) - Init")
    measure_activity(duration=10)
    print("DEBUG: Monitorando atividade de entrada (10s) - End")
    print(f"DEBUG: click_rate={metrics.get('click_rate')}, keypress_rate={metrics.get('keypress_rate')}, mouse_activity={metrics.get('mouse_activity')}")

    print("DEBUG: Coletando info do sistema - Init")
    metrics.update({
        "operation_sys": platform.system(),
        "os_version": platform.release(),
        "architecture": platform.machine(),
        "host_name": platform.node(),
        "processor": platform.processor(),
        "physical_nuclei": psutil.cpu_count(logical=False),
        "logical_nuclei": psutil.cpu_count(logical=True)
    })
    try:
        metrics["cpu_frequency"] = psutil.cpu_freq().current
    except Exception:
        pass
    print("DEBUG: Coletando info do sistema - End")

    # --- Trecho CORRIGIDO para extract_win.py ---
    print("DEBUG: Coletando uso de disco - Init")
    # Inicializa as chaves esperadas pelo servidor como None
    metrics["disk_usage_root"] = None
    metrics["disk_usage_home"] = None
    metrics["disk_usage_boot"] = None

    for part in psutil.disk_partitions(all=False):
        try:
            # Trata a unidade C: como a partição root
            if 'c:' in part.mountpoint.lower():
                metrics["disk_usage_root"] = psutil.disk_usage(part.mountpoint).percent
            # Você pode adicionar lógicas para outras partições se necessário
        except Exception as e:
            print(f"AVISO: Falha ao ler disco {part.device}: {e}")
            continue
    print("DEBUG: Coletando uso de disco - End")

    print("DEBUG: Coletando S.M.A.R.T. - Init")
    get_smart_status()
    print(f"DEBUG: smart_overall -> {metrics.get('smart_overall')}")
    print("DEBUG: Coletando S.M.A.R.T. - End")

    print("DEBUG: Coletando bateria - Init")
    try:
        battery = psutil.sensors_battery()
        if battery:
            metrics.update({
                "battery_perc": battery.percent,
                "is_charging": battery.power_plugged,
                "battery_time": battery.secsleft if not battery.power_plugged else None
            })
            print(f"DEBUG: battery_perc={battery.percent}, is_charging={battery.power_plugged}, secsleft={battery.secsleft}")
        get_battery_health(c)
        print(f"DEBUG: battery_health -> {metrics.get('battery_health')}")
    except Exception as e:
        print(f"AVISO: Falha ao coletar bateria: {e}")
    print("DEBUG: Coletando bateria - End")

    print("DEBUG: Coletando informações da placa-mãe - Init")
    try:
        board = c.Win32_BaseBoard()[0]
        system_info = c.Win32_ComputerSystem()[0]
        metrics.update({
            "motherboard_manuf": board.Manufacturer,
            "motherboard_name": board.Product,
            "motherboard_snum": board.SerialNumber.strip(),
            "motherboard_version": board.Version,
            "model": system_info.Model
        })
        try:
            metrics["serial_number"] = get_serial_number(c)
        except NameError:
            serial_final = board.SerialNumber.strip() if (board.SerialNumber and len(board.SerialNumber.strip()) > 4) else None
            if not serial_final:
                serial_final = gerar_identificador_unico(c)
            metrics["serial_number"] = serial_final
        print(f"DEBUG: motherboard_snum={metrics.get('motherboard_snum')}, serial_number={metrics.get('serial_number')}")
    except Exception as e:
        metrics["serial_number"] = gerar_identificador_unico(c)
        print(f"AVISO: Falha ao coletar dados da placa-mãe: {e}")
    print("DEBUG: Coletando informações da placa-mãe - End")

    print("DEBUG: Coletando antivírus - Init")
    metrics["antivirus_status"] = get_antivirus_status()
    print(f"DEBUG: antivirus_status -> {metrics.get('antivirus_status')}")
    print("DEBUG: Coletando antivírus - End")

    print("DEBUG: Coletando firewall - Init")
    try:
        output = subprocess.run(
            ['netsh', 'advfirewall', 'show', 'allprofiles'],
            capture_output=True, text=True, check=True,
            encoding='cp850', errors='ignore'
        ).stdout

        metrics["firewall_status_info"] = output.strip() # Armazena o output completo

        is_active = False
        # Itera sobre cada linha do output para encontrar um perfil ativo
        for line in output.splitlines():
            line_upper = line.upper()
            # Procura por "ESTADO" e "LIGADO" na mesma linha
            if 'ESTADO' in line_upper and 'LIGADO' in line_upper:
                is_active = True
                break # Encontrou um perfil ativo, pode parar a verificação
            # Adiciona verificação para o inglês também
            if 'STATE' in line_upper and 'ON' in line_upper:
                is_active = True
                break

        metrics["firewall_active"] = is_active
    except Exception as e:
        print(f"AVISO: Falha ao coletar info do firewall: {e}")
    print("DEBUG: Coletando firewall - End")

    print("DEBUG: Consultando falhas de login - Init")
    get_failed_logins(c)
    print(f"DEBUG: failed_logins -> {metrics.get('failed_logins')}")
    print("DEBUG: Consultando falhas de login - End")

    print("DEBUG: Coletando softwares instalados - Init")
    metrics["installed_softwares"] = get_installed_software()
    print(f"DEBUG: Softwares coletados: {len(metrics.get('installed_softwares', []))}")
    print("DEBUG: Coletando softwares instalados - End")

    print("DEBUG: Coletando OS patches - Init")
    try:
        metrics["os_patches"] = [p.HotFixID for p in c.Win32_QuickFixEngineering()]
        print(f"DEBUG: os_patches -> {metrics.get('os_patches')}")
    except Exception as e:
        metrics["os_patches"] = []
        print(f"AVISO: Falha ao coletar os_patches: {e}")
    print("DEBUG: Coletando OS patches - End")

    print("DEBUG: Coletando GPU via NVML - Init")
    try:
        if pynvml is not None:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            metrics.update({
                "gpu_name": pynvml.nvmlDeviceGetName(handle),
                "gpu_temperature": pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU),
                "gpu_usage": (mem_info.used / mem_info.total) * 100,
                "gpu_memory": mem_info.total
            })
            #try:
                #metrics["instant_power_consumption"] = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
            #except:
                #pass
            try:
                metrics["fan_rpm_gpu"] = pynvml.nvmlDeviceGetFanSpeed(handle)
            except:
                pass
            pynvml.nvmlShutdown()
            print(f"DEBUG: GPU NVIDIA encontrada: {metrics.get('gpu_name')}")
        else:
            print("DEBUG: pynvml não disponível, pulando coleta de NVIDIA via NVML.")
    except Exception as e:
        print(f"DEBUG: Erro ao coletar dados da GPU via NVML: {e}")
    print("DEBUG: Coletando GPU via NVML - End")

    print("DEBUG: Coletando GPU integrada via WMI - Init")
    try:
        get_integrated_gpu_name(c)
        print(f"DEBUG: inter_gpu_name -> {metrics.get('inter_gpu_name')}")
    except Exception as e:
        print(f"AVISO: Falha ao coletar GPU integrada: {e}")
    print("DEBUG: Coletando GPU integrada via WMI - End")

    print("DEBUG: Coletando temperatura da CPU - Init")
    get_cpu_temperature_wmi()
    print(f"DEBUG: cpu_temperature -> {metrics.get('cpu_temperature')}")
    print("DEBUG: Coletando temperatura da CPU - End")

    print("DEBUG: Coletando Potência Instantânea - Init")
    get_instant_power_consumption(metrics)
    print("DEBUG: Potência Instantânea ->", metrics.get("instant_power_consumption"))
    print("DEBUG: Coletando Potência Instantânea - End")

    print("DEBUG: Finalizando métricas - Init")
    metrics["time"] = time.time()
    metrics = sanitize_json_values(metrics)
    print("DEBUG: Finalizando métricas - End")

    print("\n--- Métricas Coletadas ---")
    for key, value in metrics.items():
        if value is not None and value not in ({}, []):
            print(f"{key}: {value}")

    print("\n--- Métricas Não Coletadas ---")
    for key, value in metrics.items():
        if value is None:
            print(f"{key}: {value}")

    print("--- Fim da Execução da Coleta ---")

    load_dotenv()
    API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/coletar-metricas/")
    params = {"id_empresa": os.getenv("COMPANY_ID"), "label_maquina": os.getenv("DEVICE_LABEL")}
    if not all(params.values()):
        print("\nERRO: Variáveis de ambiente COMPANY_ID ou DEVICE_LABEL não definidas. Envio cancelado.")
    else:
        try:
            print("\nDEBUG: Enviando métricas para a API - Init")
            response = requests.post(API_URL, params=params, json=metrics, timeout=20)
            response.raise_for_status()
            print("Dados enviados com sucesso!")
            print("Resposta da API:", response.json())
            print("DEBUG: Enviando métricas para a API - End")
        except requests.exceptions.RequestException as err:
            print(f"ERRO AO ENVIAR DADOS: {err}")

    print("\n--- Script Finalizado ---")