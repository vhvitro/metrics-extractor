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
    ```
    - `SUPABASE_URL`: Your Supabase project URL.
    - `SUPABASE_KEY`: Your Supabase API key.

3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Activate the uvicorn server**
    ```bash
    uvicorn main:app --reload
    ```

5. **Run the project**
    ```bash
    # If on linux
    python3 extract_linux.py
    # If on windows
    python extract_win.py
    ```
