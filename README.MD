# Catálogo de Imágenes con Clasificación IA

Aplicación Django REST + Lambda que clasifica imágenes automáticamente usando Claude (Anthropic).

---

## Estructura del proyecto

```
.
├── catalogo/
│   ├── templates/catalogo/index.html   ← Frontend completo
│   ├── models.py
│   ├── views.py                        ← ViewSet + classify_local
│   ├── serializers.py
│   └── urls.py
├── config/
│   ├── settings.py
│   └── urls.py
├── lambda/
│   ├── lambda_function.py              ← Función Lambda
│   └── requirements.txt
└── README.md
```

---

## Parte 1: Backend Django

### Variables de entorno necesarias (`.env`)

```env
DJANGO_SECRET_KEY=tu-clave-secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,<IP-de-Lightsail>
GEMINI_API_KEY=AIza...
LAMBDA_URL=https://<api-id>.execute-api.<region>.amazonaws.com/prod/classify
```

> **Obtener clave Gemini GRATIS**: https://aistudio.google.com/app/apikey → Sign in con Google → Create API Key. No requiere tarjeta de crédito.

### Correr en local

```bash
pip install django djangorestframework pillow anthropic python-dotenv
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Accede a `http://localhost:8000` para ver el frontend.

---

## Parte 2: Despliegue en AWS Lightsail (sin usuario IAM)

> **No necesitas crear un usuario IAM** para este despliegue. Lightsail usa credenciales de tu cuenta root o de consola directamente.

### Paso 1 — Crear instancia Lightsail

1. Entra a https://lightsail.aws.amazon.com
2. **Create instance** → Linux/Unix → **OS Only** → Ubuntu 22.04
3. Elige el plan de **$5/mes** (512 MB RAM es suficiente para un deber)
4. Nombre: `catalogo-django`
5. Clic en **Create instance**

### Paso 2 — Abrir el puerto 8000 (o 80)

1. En tu instancia → pestaña **Networking**
2. **Add rule** → Puerto `8000`, protocolo TCP → Save
   *(Opcional: también abre el 80 para usar nginx)*

### Paso 3 — Conectarte y configurar el servidor

Usa el terminal web de Lightsail (botón **Connect**) o SSH:

```bash
# Instalar dependencias
sudo apt update && sudo apt install python3-pip python3-venv git -y

# Clonar tu repo de GitHub
git clone https://github.com/<tu-usuario>/<tu-repo>.git
cd <tu-repo>

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate
pip install django djangorestframework pillow gunicorn

# Variables de entorno
cat > .env << 'EOF'
DJANGO_SECRET_KEY=cambia-esto-por-algo-seguro
DEBUG=False
ALLOWED_HOSTS=<IP-de-tu-instancia>
GEMINI_API_KEY=AIza...
LAMBDA_URL=https://<api-id>.execute-api.<region>.amazonaws.com/prod/classify
EOF

# Preparar la app
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

# Correr con gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --daemon
```

Tu app estará en `http://<IP-de-tu-instancia>:8000`

### (Opcional) Correr en background con systemd

```bash
sudo nano /etc/systemd/system/django.service
```

```ini
[Unit]
Description=Django Catálogo
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/<tu-repo>
EnvironmentFile=/home/ubuntu/<tu-repo>/.env
ExecStart=/home/ubuntu/<tu-repo>/venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable django
sudo systemctl start django
```

---

## Parte 3: Función Lambda

### Preparar el paquete ZIP

```bash
cd lambda/
zip lambda_deploy.zip lambda_function.py
```

> **No necesita librerías externas**. Gemini se llama con `urllib` que ya viene en Python 3.11.

### Crear la función en AWS Console (sin IAM, desde tu cuenta)

1. Ve a https://console.aws.amazon.com/lambda
2. **Create function** → Author from scratch
   - Nombre: `classify-image`
   - Runtime: **Python 3.11**
   - Architecture: x86_64
3. En **Code** → **Upload from** → .zip file → sube `lambda_deploy.zip`
4. Handler: `lambda_function.lambda_handler`

### Variables de entorno en Lambda

En la función → pestaña **Configuration** → **Environment variables**:

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | `AIza...` (de aistudio.google.com) |
| `DJANGO_API_URL` | `http://<IP-Lightsail>:8000/api/imagenes/` |

### Crear API Gateway (URL pública para Lambda)

1. Ve a **API Gateway** → **Create API** → **HTTP API**
2. Integration: Lambda → selecciona `classify-image`
3. Route: `POST /classify`
4. **Deploy** → copia la URL generada
5. Pon esa URL en tu `.env` como `LAMBDA_URL`

> **Sin usuario IAM**: API Gateway + Lambda no requieren usuario IAM para este flujo. La Lambda se invoca via HTTP público. La consola AWS usa tus credenciales de cuenta root.

---

## Flujo completo

```
Usuario sube imagen en el browser
        ↓
Frontend (HTML/JS) llama a Lambda URL con imagen en base64
        ↓
Lambda envía imagen a Claude API (Anthropic)
        ↓
Claude responde: { tipo_detectado, descripcion }
        ↓
Lambda POST a Django API: guarda tipo y descripcion
        ↓
Frontend muestra resultado y recarga el catálogo
```

---

## Endpoints API

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/imagenes/` | Listar todas |
| POST | `/api/imagenes/` | Crear (multipart con `archivo`) |
| GET | `/api/imagenes/{id}/` | Detalle |
| PUT | `/api/imagenes/{id}/` | Actualizar |
| DELETE | `/api/imagenes/{id}/` | Eliminar |
| POST | `/api/classify/` | Clasificar localmente con Claude |

---

## Capturas / Evidencia
