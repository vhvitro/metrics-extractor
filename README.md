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

5. **Configure the scheduler**

    Run the following commands inside the `metrics-extractor` directory (you will need root/admin privileges to do so).

    **Linux:**
    ```bash
    sudo crontab -l | { cat; echo "@reboot source $(pwd)/bledot-env/bin/activate; uvicorn main:app --app-dir $(pwd); deactivate # Bledot - Server"; } | sudo crontab -
    sudo crontab -l | { cat; echo "0 * * * * source $(pwd)/bledot-env/bin/activate; python $(pwd)/extract_linux.py; deactivate # Bledot - Metrics Extractor"; } | sudo crontab -
    ```

    **Windows:**
    ```bash
    schtasks /create /SC ONSTART /TN "Bledot - Server" / TR "cmd.exe /c '%CD%\bledot-env\Scripts\activate & uvicorn main:app --app-dir %CD% & deactivate'" /RU SYSTEM /RL HIGHEST
    schtasks /create /SC HOURLY /TN "Bledot - Metrics Extractor" /TR "cmd.exe /c '%CD%\bledot-env\Scripts\activate & python %CD%\extract_win.py & deactivate'" /RL HIGHEST
    ```

    Note: if you see any messages like "no crontab for root", don't worry: the script will run just fine.

6. **Run the `deactivate` command and reboot**

    After this, the metrics extractor and uvicorn server should be installed and scheduled correctly.
