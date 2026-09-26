# Dockerfile

# Usar una imagen base oficial de Python
FROM python:3.11

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos de requerimientos
COPY requirements.txt .

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . .

# Configurar las variables de entorno
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Exponer el puerto que utilizará Daphne
EXPOSE 8000

# Comando para ejecutar la aplicación usando Daphne
CMD ["python", "manage.py", "runserver"]
