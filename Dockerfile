# Gunakan base image yang sudah include Playwright dan browsers
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy requirements dan install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy aplikasi
COPY . .

# Browsers sudah ter-install di base image ini
# Tapi verifikasi sekali lagi
RUN playwright install chromium --force || echo "Browser installation check completed"

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]