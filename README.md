# Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/vhvitro/metrics-extractor.git
   cd metrics-extractor

2. **Create a `.env` file in the project root**

    Copy the example below and update with your values:
    ```properties
    SUPABASE_URL="your_supabase_url"
    SUPABASE_KEY="your_supabase_key"
    COMPANY_ID="your_company_id"
    DEVICE_LABEL="your-device-label"
    ```
    - `SUPABASE_URL`: Your Supabase project URL.
    - `SUPABASE_KEY`: Your Supabase API key.
    - `COMPANY_ID`: ID of the company that manages your device.
    - `DEVICE_LABEL`: Your device's label.

3. **Create and activate the virtual environment (venv)**
    
    **Linux:**
    ```bash
    python -m venv bledot-env
    source ./bledot-env/bin/activate
    ```

    **Windows:**
    ```bash
    python -m venv bledot-env
    .\bledot-env\Scripts\activate
    ```

4. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

5. **Configure the server service**

    Run the appropriate script (`configure_linux.sh` for Linux, `configure_win.bat` for Windows) inside the `server_config` directory with root/admin privileges.

6. **Configure the script scheduler**

    Run the following command inside the `metrics-extractor` directory (you will need root/admin privileges to do so).

    **Linux:**

    ```bash
    cd linux && chmod +x *.sh && sudo ./install_permissions.sh && ./configure_user_service.sh
    ```

    **Windows:**

    ```bash
    schtasks /create /SC HOURLY /TN "Bledot - Metrics Extractor" /TR "cmd.exe /c '%CD%\bledot-env\Scripts\activate & python %CD%\windows\extract_win.py & deactivate'" /RL HIGHEST
    ```

7. **Run the `deactivate` command and reboot**

    After this, the metrics extractor and uvicorn server should be installed and scheduled correctly.

**Deactiving the scheduler**

    If you want stop the service, run the following command inside the `metrics-extractor` directory (you will need root/admin privileges to do so).

    **Linux:**

    ```bash
    cd linux && ./configure_user_service.sh --uninstall && sudo ./install_permissions.sh --uninstall
    ```

    **Windows:**

    ```bash
    schtasks /delete /tn "Bledot - Metrics Extractor"
    ```
