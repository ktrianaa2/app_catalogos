"""
Lambda function: classify_image
Runtime: Python 3.11
Handler: lambda_function.lambda_handler

Environment variables required:
  GEMINI_API_KEY  - tu clave de Google AI Studio (gratis en https://aistudio.google.com/app/apikey)
  DJANGO_API_URL  - e.g. http://<your-lightsail-ip>/api/imagenes/

No necesita librerías externas: usa solo urllib (built-in de Python).
"""

import json
import os
import urllib.request
import urllib.error

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
DJANGO_API_URL = os.environ.get('DJANGO_API_URL', '')

CORS_HEADERS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
}


def lambda_handler(event, context):
    # ── CORS preflight ──────────────────────────────────────
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': '{}'}

    try:
        body = json.loads(event.get('body', '{}'))
    except Exception:
        body = event  # direct invocation

    image_b64 = body.get('image_b64', '')
    filename  = body.get('filename', 'imagen.jpg')
    nombre    = body.get('nombre', filename.rsplit('.', 1)[0])

    if not image_b64:
        return _resp(400, {'error': 'image_b64 is required'})

    # ── Classify with Claude ────────────────────────────────
    tipo, descripcion = classify_with_gemini(image_b64)

    result = {
        'tipo_detectado': tipo,
        'descripcion':    descripcion,
        'nombre':         nombre,
        'filename':       filename,
    }

    # ── Save to Django API ──────────────────────────────────
    if DJANGO_API_URL:
        saved = save_to_django(nombre, tipo, descripcion)
        result['saved'] = saved

    return _resp(200, result)


def classify_with_gemini(image_b64: str):
    """Usa Gemini 1.5 Flash (gratuito) para clasificar la imagen."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    )

    prompt = (
        "Clasifica esta imagen en una de estas categorías: "
        "Documento, Foto, Factura, Diagrama, Captura de Pantalla, Otro. "
        "Responde SOLO con JSON válido sin markdown: "
        '{"tipo_detectado": "<categoría>", "descripcion": "<descripción breve en español, máx 100 chars>"}'
    )

    payload = json.dumps({
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                {"text": prompt}
            ]
        }],
        "generationConfig": {"maxOutputTokens": 200, "temperature": 0.1}
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        return result.get("tipo_detectado", "Otro"), result.get("descripcion", "")
    except Exception as e:
        return "Otro", f"Error Gemini: {str(e)}"


def save_to_django(nombre: str, tipo: str, descripcion: str) -> bool:
    """POST classification results to the Django REST API."""
    if not DJANGO_API_URL:
        return False
    try:
        payload = json.dumps({
            'nombre':       nombre,
            'tipo_detectado': tipo,
            'descripcion':  descripcion,
        }).encode('utf-8')

        req = urllib.request.Request(
            DJANGO_API_URL,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 201
    except Exception:
        return False


def _resp(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': CORS_HEADERS,
        'body': json.dumps(body),
    }