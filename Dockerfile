FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias sistema
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Asegurar génesis determinístico
RUN cp blockchain_fixed.py blockchain.py || true

# Exponer puerto
EXPOSE 5000

# Variables entorno
ENV HOST=0.0.0.0
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

# Comando por defecto - nodo seed público minando
CMD ["python", "main_multinodo.py", "--host", "0.0.0.0", "--port", "5000", "--mining", "--difficulty", "4"]
