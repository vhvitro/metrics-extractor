import psutil
# Informações da GPU (para NVIDIA)
from pynvml import *
import pynvml
import GPUtil
import time
import socket
#Informações de GPU (para AMD), so importa se tiver o driver da AMD
#amdgpu-py
#import pyadl
# Obter informações do OS
import sys
# Para usar comandos no shell
import subprocess
import platform
# Captura de eventos (mouse, teclado)
import pynput
import threading
import time
from pynput import mouse, keyboard
# Para rede
import re
# Requisições
import requests

# Metricas exportadas
metrics = {
    #Tempo (Volátil)
    "time": None,

    #CPU e RAM (Volátil)
    "cpu_temperature": None,
    "cpu_usage": None,
    "ram_usage": None,
    "swap_usage": None,
    "disk_usage_root": None,
    "disk_usage_home": None,
    "disk_usage_boot": None,
    "cpu_frequency": None,
    "fan_rpm_cpu": None,


    #Placa de vídeo dedicada (Volátil)
    "fan_rpm_gpu": None,
    "gpu_temperature": None,
    "gpu_usage": None,
    "gpu_voltage": None,
    "gpu_memory": None,
    "os_patches": None,

    #SSD (Volátil)
    "smart_overall": None,
    "ssd_perc_lifetime": None,
    "ssd_power_hours": None,
    "ssd_unsafe_shutdowns": None,
    "ssd_irrecuperable_errors": None,
    "ssd_log_errors": None,

    #Bateria (Volátil)
    "battery_health": None,
    "battery_time": None,
    "battery_perc": None,
    "is_charging": None,
    "uptime": None,
    "instant_power_consumption": None, #Calcular entre duas medidas

    #Atividade (Volátil)
    "click_rate": None,
    "keypress_rate": None,
    "mouse_activity": None,

    #Endereço e Segurança (Volátil)
    "host_list": None,
    "ping_list": None,
    "pkg_loss_list": None,
    "mac": None,
    "ip4": None,
    "ipv6": None,
    "failed_logins": None,
    "antivirus_status": None, #Não achado ainda
    "firewall_active": None,
    "firewall_status_info": None,

    #Propriedade (Fixo)
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

    #Placa mãe e placa de vídeo integrada (Fixo)
    "motherboard_manuf": None,
    "motherboard_name": None,
    "motherboard_snum": None,
    "mb_is_replaceable": None,
    "mb_is_a_hosting_b": None,
    "mb_loc_chassis": None,
    "motherboard_version": None,
    "chassis_handle": None,
    "inter_gpu_name": None,

    #Configurações de fábrica (Fixo)
    "serial_number": None,
    "model": None,

    #Estado do Hardware (Volátil)
    "hardware_config": None,     #Falta AMD
    "recent_hardware_failures": None,

    #Softwares instalados (volátil)
    "installed_softwares": None,

    #Localização (Volátil)
    "country": None,
    "region_name": None,
    "city": None,
    "lat": None,
    "lon": None
}

#Temperatura CPU
print("DEBUG: Temperatura CPU - Init")
temperatures = psutil.sensors_temperatures()
try:
    if 'coretemp' in temperatures:
        metrics["cpu_temperature"] = temperatures['coretemp'][0].current
    else:
        print("ERRO: Sensor de temperatura da CPU não encontrado")
except Exception as e:
    print("ERRO: ", e)
print("DEBUG: Temperatura CPU - End")
#Uso RAM
print("DEBUG: Uso de RAM - Init")
try:
    info_ram = psutil.virtual_memory()
    metrics["ram_usage"] = info_ram.percent/100
except Exception as e:
    print("ERRO: ", e)
print("DEBUG: Uso de RAM - End")
#Uso CPU
print("DEBUG: Uso de CPU - Init")
try:
    metrics["cpu_usage"] = psutil.cpu_percent(interval=1)/100
except Exception as e:
    print("ERRO: ", e)
print("DEBUG: Uso de CPU- End")
#Uso de SSD/HD
print("DEBUG: Uso de SSD/HD - Init")
try:
    info_particoes = psutil.disk_partitions()
    for particao in info_particoes:
        if particao.mountpoint == '/':
            metrics["disk_usage_root"] = psutil.disk_usage(particao.mountpoint).percent/100
        elif particao.mountpoint == '/home':
            metrics["disk_usage_home"] = psutil.disk_usage(particao.mountpoint).percent/100
        elif particao.mountpoint == '/boot/efi':
            metrics["disk_usage_boot"] = psutil.disk_usage(particao.mountpoint).percent/100
except Exception as e:
    print("ERRO: ", e)
print("DEBUG: Uso de SSD/HD - End")
#Uso de Swap:
print("DEBUG: Uso de SWAP - Init")
try:
    info_swap = psutil.swap_memory()
    metrics["swap_usage"] = info_swap.percent/100
    metrics["swap_total"] = info_swap.total
except Exception as e:
    print(f"ERROR: {e}")
print("DEBUG: Uso de SWAP - End")
#Tempo Ligado:
print("DEBUG: Tempo Ligado - Init")
try:
    t_boot = psutil.boot_time()
    t_atual = time.time()
    metrics["uptime"] = t_atual - t_boot
except Exception as e:
    print("ERRO: ", e)
print("DEBUG: Tempo Ligado - End")
#Ventoinhas
print("DEBUG: Ventoinhas - Init")
try:
    info_vent = psutil.sensors_fans()
    for names, fans in info_vent.items():
        for fan in fans:
            if fan.label == 'cpu_fan':
                metrics["fan_rpm_cpu"] = fan.current
            elif fan.label == 'gpu_fan':
                metrics["fan_rpm_gpu"] = fan.current
            else:
                print(f"ALARM: Outra ventoinha detectada: Máquina: Nome: {fan.label}, Rotação: {fan.current}")
except Exception as e:
    print("ERRO: ", e)
print("DEBUG: Ventoinhas - End")

#Detectando qual a marca da GPU
print("DEBUG: GPU - Init")
marca = None
#Nvidia?
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
if marca != 'Nvidia':
    print("Tentando instalar amdgpu-py...")
    try:
        resultado = subprocess.run(
            [sys.executable, "-m", "pip", "install", "amdgpu-py"],
            capture_output=True,
            text=True,
            check=True
        )
        print("\n--- Instalação Concluída ---\n")
        print(resultado.stdout)
        print("A biblioteca amdgpu-py foi instalada com sucesso.")
    except subprocess.CalledProcessError as e:
        print("\n--- Instalação Falhou ---\n")
        print(f"Erro ao executar o comando: {e}")
        print(f"\nSaída de erro:\n{e.stderr}")
        print("A instalação da biblioteca amdgpu-py falhou.")
        if "No matching distribution found for amdgpu-py" in e.stderr:
            print("Isso geralmente acontece quando não há uma GPU AMD ou os drivers não estão instalados.")
    except FileNotFoundError:
        print("\n--- Erro de Ambiente ---\n")
        print("Comando 'pip' ou 'python' não encontrado.")
        print("Certifique-se de que o Python e o pip estão no PATH.")

# Medidas de GPU:
try:
    if marca == 'Nvidia':
        print("DEBUG: Medidas de GPU (NVIDIA) - Init")
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            device_name = pynvml.nvmlDeviceGetName(handle)
            try:
                voltage_mv = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                metrics["gpu_voltage"] = voltage_mv
            except pynvml.NVMLError as e:
                print(f"[{i}] GPU: {device_name}")
                print(f"   Não foi possível obter a tensão. Erro: {e}")
        pynvml.nvmlShutdown()

        pynvml.nvmlInit()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            metrics["gpu_name"] = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
            metrics["gpu_temperature"] = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            metrics["gpu_usage"] = (mem_info.used / mem_info.total)
            metrics["gpu_memory"] = mem_info.total
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
    else:
        print("DEBUG: Nenhuma GPU NVIDIA detectada, pulando medidas específicas.")
except Exception as e:
    print(f"Erro ao acessar GPU: {e}")
print("DEBUG: GPU - End")

#Uso de bateria
print("DEBUG: Bateria - Init")
try:
    result = subprocess.run(
        ['upower', '-i', '/org/freedesktop/UPower/devices/battery_BAT0'],
        capture_output=True, text=True, check=True
    )
    output = result.stdout
    design_capacity_match = re.search(r'energy-full-design:\s+([\d,.]+)\s+Wh', output)
    full_capacity_match = re.search(r'energy-full:\s+([\d,.]+)\s+Wh', output)
    if design_capacity_match and full_capacity_match:
        design_capacity_str = design_capacity_match.group(1).replace(',', '.')
        full_capacity_str = full_capacity_match.group(1).replace(',', '.')
        design_capacity = float(design_capacity_str)
        full_capacity = float(full_capacity_str)
        metrics["battery_health"] = (full_capacity / design_capacity)
    else:
        print("Não foi possível encontrar os dados de capacidade da bateria.")
except FileNotFoundError:
    print("O comando 'upower' não foi encontrado. Certifique-se de que ele está instalado.")
except subprocess.CalledProcessError as e:
    print(f"Erro ao executar 'upower': {e}")
try:
    info_bateria = psutil.sensors_battery()
    metrics["battery_perc"] = info_bateria.percent
    metrics["is_charging"] = info_bateria.power_plugged
    if metrics["is_charging"]:
        metrics["battery_time"] = float('inf')
    else:
        metrics["battery_time"] = info_bateria.secsleft
except Exception as e:
    print(f"ERRO: {e}")
print("DEBUG: Bateria - End")

#Localização
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
    else:
        print("Não foi possível obter a localização. Verifique sua conexão com a internet.")
except requests.exceptions.RequestException as e:
    print(f"Erro ao conectar com a API: {e}")
print("DEBUG: Localização - End")

#Falhas de Hardware
print("DEBUG: Falhas de Hardware - Init")
try:
    hardware_errors = 0
    command = ["sudo", "journalctl", "--since", "10 min ago", "--no-pager"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    log_lines = result.stdout.strip().split('\n')
    log_pattern = re.compile(
        r'.*(?:hardware error|kernel BUG|unrecoverable error|machine check|bus error|io error|memory error|disk error).*',
        re.IGNORECASE
    )
    for line in log_lines:
        if log_pattern.search(line):
            print(f"DEBUG: Erro de hardware detectado: {line}")
            hardware_errors += 1
    metrics['recent_hardware_failures'] = hardware_errors
except (subprocess.CalledProcessError, FileNotFoundError) as e:
    print("\n--- ERRO: Verificação de Falhas de Hardware ---")
    print(f"Erro ao extrair eventos de hardware: {e}", file=sys.stderr)
    print("Possíveis causas: ")
    if isinstance(e, subprocess.CalledProcessError):
        print("  - Você não tem permissões de 'sudo'. Tente executar o script com 'sudo python'.")
        print(f"  - Saída do comando: {e.stderr}", file=sys.stderr)
    elif isinstance(e, FileNotFoundError):
        print(
            "  - O comando 'journalctl' não foi encontrado. Certifique-se de que o sistema é Linux e o comando está no PATH.")
print("DEBUG: Falhas de Hardware - End")

#IP e endereço MAC
print("DEBUG: Endereços - Init")
try:
    interfaces = psutil.net_if_addrs()
    for interface_name, interface_addresses in interfaces.items():
        if interface_name.startswith('lo') or interface_name.startswith('docker'):
            continue
        for address_info in interface_addresses:
            if address_info.family == socket.AF_INET:
                metrics["ipv4"] = address_info.address
            elif address_info.family == socket.AF_INET6:
                metrics["ipv6"] = address_info.address
            elif address_info.family == psutil.AF_LINK:
                metrics["mac"] = address_info.address
    if "ipv4" not in metrics and "ipv6" not in metrics:
        print("ALARM: Nenhum endereço IP principal foi encontrado.")
except Exception as e:
    print(f"Erro ao ler informações de rede: {e}")
print("DEBUG: Endereço - End")

#Numero de série e modelo
print("DEBUG: Serial/Modelo - Init")
try:
    cmd_chassi = ["sudo", "dmidecode", "-t", "chassis"]
    cmd_system = ["sudo", "dmidecode", "-t", "system"]
    result_chassi = subprocess.run(cmd_chassi, capture_output=True, text=True, check=True)
    match_chassi = [line for line in result_chassi.stdout.split('\n') if "Serial Number:" in line]
    if match_chassi:
        metrics['serial_number'] = match_chassi[0].split(":")[1].strip()
    result_system = subprocess.run(cmd_system, capture_output=True, text=True, check=True)
    match_system = [line for line in result_system.stdout.split('\n') if "Product Name:" in line or "Serial Number:" in line]
    for line in match_system:
        if "Product Name:" in line:
            metrics['model'] = line.split(":")[1].strip()
        if "Serial Number:" in line:
            metrics['serial_number'] = line.split(":")[1].strip()
except (subprocess.CalledProcessError, FileNotFoundError) as e:
    print(f"Erro ao executar o dmidecode. Certifique-se de que está instalado e o script roda com sudo. Detalhes: {e}")
print("DEBUG: Serial/Modelo - End")

#Informaçoes de OS, CPU e Memória
print("DEBUG: Info OS/CPU/Memória - Init")
try:
    metrics["operation_sys"] = platform.system()
    metrics["os_version"] = platform.release()
    metrics["architecture"] = platform.machine()
    metrics["host_name"] = platform.node()
    metrics["processor"]  = platform.processor()
    metrics["physical_nuclei"] = psutil.cpu_count(logical=False)
    metrics["logical_nuclei"] = psutil.cpu_count(logical=True)
    try:
        metrics["cpu_frequency"] = psutil.cpu_freq().current
    except AttributeError:
        print("Frequência da CPU não disponível.")
    metrics["total_memory"] = psutil.virtual_memory().total
except Exception as e:
    print(f"ERROR: {e}")
print("DEBUG: Info OS/CPU/Memória - End")

#Placa mãe
print("DEBUG: Placa-mãe - Init")
try:
    command = ['sudo', 'dmidecode', '-t', '2']
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    output = result.stdout
    manuf_match = re.search(r'Manufacturer:\s+(.*)', output)
    if manuf_match:
        metrics["motherboard_manuf"] = manuf_match.group(1).strip()
    name_match = re.search(r'Product Name:\s+(.*)', output)
    if name_match:
        metrics["motherboard_name"] = name_match.group(1).strip()
    version_match = re.search(r'Version:\s+(.*)', output)
    if version_match:
        metrics["motherboard_version"] = version_match.group(1).strip()
    snum_match = re.search(r'Serial Number:\s+(.*)', output)
    if snum_match:
        metrics["motherboard_snum"] = snum_match.group(1).strip()
    replaceable_match = re.search(r'Board is removable', output)
    metrics["mb_is_replaceable"] = bool(replaceable_match)
    hosting_match = re.search(r'Board is a hosting board', output)
    metrics["mb_is_a_hosting_b"] = bool(hosting_match)
    loc_match = re.search(r'Location In Chassis:\s+(.*)', output)
    if loc_match:
        metrics["mb_loc_chassis"] = loc_match.group(1).strip()
    handle_match = re.search(r'Chassis Handle:\s+(.*)', output)
    if handle_match:
        metrics["chassis_handle"] = handle_match.group(1).strip()
except subprocess.CalledProcessError as e:
    print(f"ERRO: Erro ao executar o comando. Saída de erro:\n{e.stderr}", file=sys.stderr)
    print("Certifique-se de que tem permissões de sudo.")
except FileNotFoundError:
    print("ERRO: Comando 'dmidecode' não encontrado. Instale-o com 'sudo apt install dmidecode'.")
print("DEBUG: Placa-mãe - End")

#GPU interna
print("DEBUG: GPU Interna - Init")
try:
    command = ['lspci', '-v']
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    output = result.stdout
    log_pattern = re.compile(r'VGA compatible controller:\s+(.*)', re.IGNORECASE)
    for line in output.split('\n'):
        match = log_pattern.search(line)
        if match:
            gpu_name = match.group(1).strip()
            metrics["inter_gpu_name"] = gpu_name
            break
    if metrics["inter_gpu_name"] is None:
        print("ALERTA: Nenhuma GPU integrada (VGA) foi detectada.")
except (subprocess.CalledProcessError, FileNotFoundError) as e:
    print(f"ERRO: Erro ao extrair informações da GPU: {e}", file=sys.stderr)
    print("Certifique-se de que o comando 'lspci' está disponível e acessível.")
print("DEBUG: GPU Interna - End")

#Tentativas de login falhas
print("DEBUG: Tentativas de Login - Init")
failed_attempts = []
command = ["sudo", "journalctl", "--since", "10 min ago", "--no-pager"]
try:
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    log_lines = result.stdout.strip().split('\n')
    log_pattern = re.compile(
        r'.* (?:gdm-password|sshd|sudo).* (?:authentication failure|Failed password).*',
        re.IGNORECASE
    )
    for line in log_lines:
        if log_pattern.search(line):
            failed_attempts.append(line.strip())
    metrics["failed_logins"] = len(failed_attempts)
except (subprocess.CalledProcessError, FileNotFoundError) as e:
    print(f"Erro ao tentar extrair logs: {e}")
print("DEBUG: Tentativas de Login - End")

#Inventário de softwares
print("DEBUG: Inventário de Softwares - Init")
def get_installed_software_linux():
    software_list = []
    try:
        if os.path.exists('/usr/bin/dpkg'):
            command = "dpkg-query -f '${binary:Package}\n' -W"
            output = subprocess.check_output(command, shell=True, text=True, errors='ignore')
            software_list = output.strip().split('\n')
        elif os.path.exists('/usr/bin/rpm'):
            print("Detectando softwares com 'rpm'...")
            command = 'rpm -qa --qf "%{NAME}\n"'
            output = subprocess.check_output(command, shell=True, text=True, errors='ignore')
            software_list = output.strip().split('\n')
        else:
            print("Nenhum gerenciador de pacotes (dpkg ou rpm) suportado foi encontrado.")
            return []
    except Exception as e:
        print(f"Ocorreu um erro ao tentar listar softwares: {e}", file=sys.stderr)
        return []
    return software_list
software_instalado = get_installed_software_linux()
if software_instalado:
    metrics["installed_softwares"] = software_instalado
else:
    print("DEBUG: Nenhuma lista de software foi retornada. Atribuindo None.")
    metrics["installed_softwares"] = None
print("DEBUG: Inventário de Softwares - End")

#Patches do SO
print("DEBUG: Patches SO - Init")
def get_update_status():
    try:
        subprocess.run(
            ['sudo', 'apt', 'update'],
            check=True,
            text=True,
            capture_output=True,
            errors='ignore'
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return []
    try:
        list_result = subprocess.run(
            ['apt', 'list', '--upgradable'],
            check=True,
            text=True,
            capture_output=True,
            errors='ignore'
        )
        upgradable_packages = list_result.stdout.strip().split('\n')
        if upgradable_packages and upgradable_packages[0].startswith("Listando"):
            upgradable_packages.pop(0)
        return upgradable_packages
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"ERRO: Falha ao listar pacotes: {e}", file=sys.stderr)
        return []
patches_pendentes = get_update_status()
if patches_pendentes:
    metrics["os_patches"] = patches_pendentes
else:
    metrics["os_patches"] = []
print("DEBUG: Patches SO - End")

#Firewall
print("DEBUG: Firewall - Init")
def get_ufw_status():
    try:
        result_which = subprocess.run(['which', 'ufw'], capture_output=True, text=True)
        if result_which.returncode != 0:
            return "UFW not installed", None
        result_ufw = subprocess.run(
            ['sudo', 'ufw', 'status'],
            capture_output=True,
            text=True,
            check=True
        )
        status_output = result_ufw.stdout.strip()
        is_active = status_output.startswith("Status: active") or status_output.startswith("Estado: ativo")
        status_lines = status_output.split('\n')
        return is_active, status_lines
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to run 'ufw status'. Error: {e.stderr}", file=sys.stderr)
        return None, ["Permission denied or UFW is not running."]
    except FileNotFoundError:
        print("ERROR: 'ufw' command not found.", file=sys.stderr)
        return None, ["Error: 'ufw' command not found."]
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}", file=sys.stderr)
        return None, ["An unexpected error occurred while checking firewall status."]
is_active, status_info = get_ufw_status()
if is_active is not None:
    metrics["firewall_active"] = is_active
else:
    metrics["firewall_active"] = None
if status_info:
    metrics["firewall_status_info"] = "\n".join(status_info)
else:
    metrics["firewall_status_info"] = None
print("DEBUG: Firewall - End")

#Smart do disco
print("DEBUG: Smart Disk - Init")
def get_smart_data_linux(device_name):
    try:
        command = ["sudo", "smartctl", "-a", device_name]
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)

        smart_data = result.stdout
        smart_status_check = subprocess.run(["sudo", "smartctl", "-H", device_name], capture_output=True, text=True,
                                            check=True, timeout=30)
        smart_status = smart_status_check.stdout

        return smart_data, smart_status

    except FileNotFoundError:
        print(f"Erro: 'smartctl' não encontrado. Por favor, instale 'smartmontools'.")
        return None, None

    except subprocess.CalledProcessError as e:
        print(f"Erro ao obter dados SMART para {device_name}.")
        print(f"Código de retorno: {e.returncode}")
        print(f"Mensagem de erro (stderr): {e.stderr.strip()}")

        if e.stdout.strip():
            print(f"Saída parcial (stdout):")
            #Output do Smart
            #print(e.stdout)
            print("Acesso pelo código fonte")
        return e.stdout, None

    except subprocess.TimeoutExpired:
        print(f"O comando smartctl para {device_name} excedeu o tempo limite de 30 segundos.")
        return None, None

    except Exception as e:
        print(f"Ocorreu um erro inesperado ao processar {device_name}: {e}")
        return None, None

def find_all_disks():
    """
    Encontra todos os dispositivos de armazenamento compatíveis.
    """
    try:
        command = ["lsblk", "-d", "-n", "-o", "NAME"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        disks = [line for line in result.stdout.splitlines() if line.startswith(('sd', 'nvme', 'hd'))]
        return disks
    except Exception as e:
        print(f"Erro ao encontrar os discos: {e}")
        return []


def parse_smart_data(output_text):
    smart_metrics = {
        "model": None,
        "serial_number": None,
        "smart_overall": None,
        "ssd_perc_lifetime": None,
        "ssd_power_hours": None,
        "ssd_unsafe_shutdowns": None,
        "ssd_irrecuperable_errors": None,
        "ssd_log_errors": None
    }

    model_match = re.search(r'Model Number:\s+(.*)', output_text)
    if model_match:
        smart_metrics['model'] = model_match.group(1).strip()

    serial_match = re.search(r'Serial Number:\s+(.*)', output_text)
    if serial_match:
        smart_metrics['serial_number'] = serial_match.group(1).strip()

    overall_match = re.search(r'SMART overall-health self-assessment test result:\s+(.*)', output_text)
    if overall_match:
        smart_metrics['smart_overall'] = overall_match.group(1).strip()

    used_match = re.search(r'Percentage Used:\s+(\d+)%', output_text)
    if used_match:
        smart_metrics['ssd_perc_lifetime'] = int(used_match.group(1))

    power_hours_match = re.search(r'Power On Hours:\s+(\d+)', output_text)
    if power_hours_match:
        smart_metrics['ssd_power_hours'] = int(power_hours_match.group(1))

    unsafe_shutdowns_match = re.search(r'Unsafe Shutdowns:\s+(\d+)', output_text)
    if unsafe_shutdowns_match:
        smart_metrics['ssd_unsafe_shutdowns'] = int(unsafe_shutdowns_match.group(1))

    media_errors_match = re.search(r'Media and Data Integrity Errors:\s+(\d+)', output_text)
    if media_errors_match:
        smart_metrics['ssd_irrecuperable_errors'] = int(media_errors_match.group(1))

    log_errors_match = re.search(r'Error Information Log Entries:\s+(\d+)', output_text)
    if log_errors_match:
        smart_metrics['ssd_log_errors'] = int(log_errors_match.group(1))

    return smart_metrics

disk_list = find_all_disks()

if not disk_list:
    print("Nenhum disco compatível encontrado para verificação SMART.")
else:
    for disk in disk_list:
        device_path = f"/dev/{disk}"
        print(f"\n--- Verificando o disco: {device_path} ---")
        smart_full_data, smart_status = get_smart_data_linux(device_path)

        if smart_full_data:
            # Chama a função de análise para obter as métricas
            smart_metrics_from_disk = parse_smart_data(smart_full_data)

            # Adiciona as métricas ao dicionário principal
            metrics.update(smart_metrics_from_disk)

# Apenas para mostrar que as variáveis foram salvas
print("DEBUG: Smart Disk - End")

#Monitoramento de input
print("DEBUG: Input Monitoring - Init")
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
    with mouse.Listener(on_click=on_click, on_move=on_move) as mouse_listener, \
            keyboard.Listener(on_press=on_press) as keyboard_listener:
        stop_event.wait(duration)
        keyboard_listener.stop()
        mouse_listener.stop()
    metrics["click_rate"] = total_clicks / duration
    metrics["keypress_rate"] = total_keypresses / duration
    metrics["mouse_activity"] = mouse_activity
measure_activity(duration=10)
print("DEBUG: Input Monitoring - End")

#Latencia e perda de dados
print("DEBUG: Perda de dados e ping - init")


def ping_network_stats(host='8.8.8.8', count=4):

    try:
        # Apenas a lógica para Linux, conforme a suposição
        cmd = ['ping', '-c', str(count), host]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return {
                'host': host,
                'status': 'falha',
                'erro': result.stderr.strip() or 'Host inacessível',
                'latencia_avg': None,
                'perda_pacotes': 100
            }

        output = result.stdout

        # Analisa a saída específica do Linux
        return _parse_ping_linux(output, host, count)

    except subprocess.TimeoutExpired:
        return {
            'host': host,
            'status': 'timeout',
            'erro': 'Comando ping expirou',
            'latencia_avg': None,
            'perda_pacotes': 100
        }

    except Exception as e:
        return {
            'host': host,
            'status': 'erro',
            'erro': str(e),
            'latencia_avg': None,
            'perda_pacotes': 100
        }


def _parse_ping_linux(output, host, count):
    """Analisa o output do ping no Linux."""
    try:
        stats_match = re.search(r'(\d+) packets transmitted, (\d+) received, (\d+(?:\.\d+)?)% packet loss', output)
        if stats_match:
            packet_loss = float(stats_match.group(3))
        else:
            packet_loss = 100

        summary_match = re.search(r'min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms', output)

        if summary_match:
            avg_lat = float(summary_match.group(2))
            return {
                'host': host,
                'status': 'sucesso',
                'perda_pacotes': packet_loss,
                'latencia_avg': avg_lat
            }
        else:
            return {
                'host': host,
                'status': 'sem_resposta',
                'perda_pacotes': packet_loss,
                'latencia_avg': None
            }
    except Exception as e:
        return {
            'host': host,
            'status': 'erro_parse',
            'erro': str(e)
        }


def get_network_metrics():

    hosts_to_test = ['8.8.8.8', '1.1.1.1', 'google.com', 'github.com']

    # Listas temporárias para armazenar os dados
    host_list_temp = []
    ping_list_temp = []
    pkg_loss_list_temp = []

    for host in hosts_to_test:
        stats = ping_network_stats(host, count=4)

        host_list_temp.append(host)

        ping_list_temp.append(stats.get('latencia_avg'))
        pkg_loss_list_temp.append(stats.get('perda_pacotes'))

    return host_list_temp, ping_list_temp, pkg_loss_list_temp


hosts, pings, perdas = get_network_metrics()

if hosts:
    metrics["host_list"] = hosts
    metrics["ping_list"] = pings
    metrics["pkg_loss_list"] = perdas
else:
    # Caso contrário, as métricas permanecem como None, conforme o inicializado.
    print("Nenhuma métrica de rede válida foi coletada. As métricas permanecem None.")

print("DEBUG: Perca de dados e ping - End")

#Tempo
metrics["time"] = time.time()

print(metrics)

for name, metric in metrics.items():
    if metric is not None:
        print("------------------------------------------")
        print(name)

"""!! Seção para enviar os dados para a API FastAPI !!""" 

# URL da API
API_URL = "http://127.0.0.1:8000/coletar-metricas/"

# IDs que identificam esta máquina e a empresa cliente
ID_DA_EMPRESA_CLIENTE = "COLOQUE_AQUI_O_UUID_DE_UMA_EMPRESA_CADASTRADA"
LABEL_DA_MAQUINA = "Notebook-Dev-Linux" # Nome amigável

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