# Catálogo de Imágenes con Clasificación IA

Aplicación Django REST desplegada en **AWS Elastic Beanstalk** con una función **AWS Lambda** que clasifica imágenes automáticamente usando **Google Gemini**.

---

## Estructura del proyecto

```
.
├── .ebextensions/
│   ├── django.config         ← Config WSGI + archivos estáticos para EB
│   └── packages.config       ← Comandos post-deploy (migrate, collectstatic, media)
├── .platform/
│   └── hooks/postdeploy/
│       └── 01_migrate.sh     ← Script de migración para EB
├── catalogo/
│   ├── templates/catalogo/
│   │   └── index.html        ← Frontend completo (HTML + CSS + JS)
│   ├── migrations/
│   ├── models.py             ← Modelo Imagen
│   ├── views.py              ← ViewSet CRUD + classify_local (Gemini)
│   ├── serializers.py
│   ├── urls.py
│   └── admin.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── lambda/
│   └── lambda_function.py   ← Función Lambda (clasificación con Gemini)
├── Procfile                  ← Comando gunicorn para EB
├── requirements.txt
├── manage.py
└── README.md
```

---

## Flujo completo de la aplicación

```
Usuario sube imagen en el browser
        ↓
Frontend llama a POST /api/classify/ (Django en EB)
        ↓
Django envía imagen en base64 a Google Gemini API
        ↓
Gemini responde: { tipo_detectado, descripcion }
        ↓
Frontend muestra tipo y descripción detectados
        ↓
Usuario hace clic en "Guardar en catálogo"
        ↓
Frontend POST a /api/imagenes/ con archivo + metadatos
        ↓
Django guarda la imagen y datos en SQLite
```

> La función Lambda es independiente: también puede recibir una imagen, clasificarla con Gemini y guardar el resultado en Django vía su API REST.

---

## Endpoints API

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/imagenes/` | Listar todas las imágenes |
| POST | `/api/imagenes/` | Crear registro (multipart con `archivo`) |
| GET | `/api/imagenes/{id}/` | Detalle de una imagen |
| PUT | `/api/imagenes/{id}/` | Actualizar |
| DELETE | `/api/imagenes/{id}/` | Eliminar |
| POST | `/api/classify/` | Clasificar imagen con Gemini IA |

---

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Clave secreta de Django |
| `DEBUG` | `True` en local, `False` en producción |
| `ALLOWED_HOSTS` | Hosts permitidos (ej: `.elasticbeanstalk.com`) |
| `GEMINI_API_KEY` | Clave de Google AI Studio (gratis) |
| `LAMBDA_URL` | URL del API Gateway que invoca la Lambda |

> **Obtener GEMINI_API_KEY gratis**: https://aistudio.google.com/app/apikey → Sign in con Google → Create API Key. No requiere tarjeta de crédito.

---

## Parte 1: Correr en local

```bash
# Instalar dependencias
pip install django djangorestframework pillow gunicorn python-dotenv

# Crear archivo .env
cat > .env << 'EOF'
DJANGO_SECRET_KEY=cualquier-string-secreto-largo
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
GEMINI_API_KEY=AIza...
LAMBDA_URL=/api/classify/
EOF

# Preparar base de datos y correr
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Accede a `http://localhost:8000`

---

## Parte 2: Despliegue en AWS Elastic Beanstalk

### Paso 1 — Obtener credenciales AWS

1. Entra a https://console.aws.amazon.com
2. Haz clic en tu nombre (esquina superior derecha) → **Security Credentials**
3. Baja hasta **Access keys** → **Create access key**
4. Selecciona **Command Line Interface (CLI)** → confirma → **Create**
5. ⚠️ Copia los dos valores ahora (el Secret solo se muestra una vez):
   - `Access Key ID`
   - `Secret Access Key`

### Paso 2 — Instalar EB CLI y configurar credenciales

```bash
pip install awsebcli

aws configure
# AWS Access Key ID: <tu key>
# AWS Secret Access Key: <tu secret>
# Default region name: us-east-1
# Default output format: json
```

### Paso 3 — Inicializar EB en el proyecto

```bash
cd <carpeta-del-proyecto>
eb init
```

Responde así cuando te pregunte:

```
Select a default region        → 1 (us-east-1)
Enter Application Name         → catalogo-imagenes
It appears you are using Python. Is this correct? → Y
Select a platform branch       → Python 3.11
Do you want to set up SSH?     → n
```

### Paso 4 — Crear el entorno

```bash
eb create catalogo-env --single
```

`--single` usa una sola instancia sin load balancer (más simple y económico). Espera ~5 minutos. Al terminar verás la URL del entorno, algo como:

```
catalogo-env.eba-xxxxxx.us-east-1.elasticbeanstalk.com
```

### Paso 5 — Configurar variables de entorno

```bash
eb setenv \
  DJANGO_SECRET_KEY="pon-aqui-un-string-largo-y-random" \
  DEBUG="False" \
  ALLOWED_HOSTS=".elasticbeanstalk.com" \
  GEMINI_API_KEY="AIza..."
```

> El `LAMBDA_URL` lo agregas después, cuando tengas la URL del API Gateway.

### Paso 6 — Abrir la app

```bash
eb open
```

### Comandos útiles

```bash
eb deploy        # redesplegar después de cambios en el código
eb status        # ver estado del entorno
eb logs          # ver logs si algo falla
eb logs --all    # logs completos
```

---

## Parte 3: Función Lambda

### Paso 1 — Crear la función

1. Ve a https://console.aws.amazon.com/lambda
2. **Create function** → **Author from scratch**
3. Completa:
   - **Function name**: `classify-image`
   - **Runtime**: Python 3.11
   - **Architecture**: x86_64
4. Clic en **Create function**

### Paso 2 — Pegar el código

1. En la función verás el editor con un archivo `lambda_function.py`
2. Haz clic en ese archivo → **Selecciona todo** (Ctrl+A) → **Borra**
3. Pega el contenido de `lambda/lambda_function.py` de este repositorio
4. Clic en el botón naranja **Deploy**

### Paso 3 — Variables de entorno en Lambda

En la función → **Configuration** → **Environment variables** → **Edit** → **Add environment variable**:

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | `AIza...` |
| `DJANGO_API_URL` | `http://catalogo-env.eba-xxx.us-east-1.elasticbeanstalk.com/api/imagenes/` |

Clic en **Save**.

### Paso 4 — Crear API Gateway (URL pública para Lambda)

1. En la función Lambda → **Configuration** → **Triggers** → **Add trigger**
2. Selecciona **API Gateway**
3. Configura:
   - **Create a new API**
   - **API type**: HTTP API
   - **Security**: Open
4. Clic en **Add**
5. En **Configuration** → **Triggers** copia la **API endpoint URL**, algo como:
   `https://abc123.execute-api.us-east-1.amazonaws.com/default/classify-image`

### Paso 5 — Actualizar EB con la URL de Lambda

```bash
eb setenv LAMBDA_URL="https://abc123.execute-api.us-east-1.amazonaws.com/default/classify-image"
```

---

## Parte 4: Probar todo

### Probar Lambda desde la consola AWS

1. En tu función Lambda → pestaña **Test** → **Create new test event**
2. Pega este JSON y haz clic en **Test**:

```json
{
  "body": "{\"image_b64\": \"data:image/jpeg;base64,/9j/4AAQ\", \"filename\": \"test.jpg\"}",
  "httpMethod": "POST"
}
```

Resultado esperado (con base64 inválido Gemini retorna error, pero confirma que el código está cargado):
```json
{
  "statusCode": 200,
  "body": "{\"tipo_detectado\": \"Otro\", \"descripcion\": \"Error Gemini: ...\", ...}"
}
```

Para probar con imagen real, convierte una foto a base64 en https://www.base64-image.de y úsala en el evento.

### Probar la app completa

1. `eb open` → abre la app en el browser
2. Sube una imagen → clic en **⚡ Clasificar con IA**
3. Verifica que aparece el tipo y descripción detectados
4. Clic en **Guardar en catálogo** → la imagen aparece en la galería

---

## Solución de problemas comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `DisallowedHost` | ALLOWED_HOSTS no incluye la URL de EB | `eb setenv ALLOWED_HOSTS=".elasticbeanstalk.com"` |
| `502 Bad Gateway` | Error en gunicorn o dependencias | `eb logs` para ver el error exacto |
| Lambda retorna `"Hello from Lambda!"` | No se pegó el código nuevo | Reemplazar el código en el editor y hacer Deploy |
| Gemini `400 Bad Request` | API key inválida o imagen corrupta | Verificar `GEMINI_API_KEY` en las env vars de Lambda |
| Imágenes no persisten al redesplegar | SQLite y media en almacenamiento local de EB | Normal para un deber; en producción se usaría S3 + RDS |

---

## Capturas / Evidencia
