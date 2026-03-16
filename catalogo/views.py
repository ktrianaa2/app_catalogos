import json
import urllib.request
import urllib.error
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render
from django.conf import settings
from .models import Imagen
from .serializers import ImagenSerializer


class ImagenViewSet(viewsets.ModelViewSet):
    queryset = Imagen.objects.all()
    serializer_class = ImagenSerializer


def index(request):
    lambda_url = getattr(settings, 'LAMBDA_URL', '')
    return render(request, 'catalogo/index.html', {'lambda_url': lambda_url})


@api_view(['POST'])
def classify_local(request):
    raw      = request.data.get('image_b64', '')
    filename = request.data.get('filename', 'imagen.jpg')

    if not raw:
        return Response({'error': 'image_b64 required'}, status=400)

    # Extraer mime_type y base64 puro de la data URL
    mime_type = 'image/jpeg'
    image_b64 = raw
    if raw.startswith('data:'):
        header, image_b64 = raw.split(',', 1)
        mime_type = header.split(';')[0].replace('data:', '')
    else:
        ext = filename.rsplit('.', 1)[-1].lower()
        mime_map = {'png': 'image/png', 'webp': 'image/webp',
                    'gif': 'image/gif', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}
        mime_type = mime_map.get(ext, 'image/jpeg')

    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return Response({
            'tipo_detectado': 'Error',
            'descripcion': 'GEMINI_API_KEY no está en el .env'
        }, status=200)

    try:
        result = classify_with_gemini(image_b64, mime_type, api_key)
        return Response(result)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return Response({'tipo_detectado': 'Desconocido',
                         'descripcion': f'Error Gemini {e.code}: {body[:300]}'}, status=200)
    except urllib.error.URLError as e:
        return Response({'tipo_detectado': 'Desconocido',
                         'descripcion': f'Sin conexión: {e.reason}'}, status=200)
    except Exception as e:
        return Response({'tipo_detectado': 'Desconocido',
                         'descripcion': f'Error: {str(e)}'}, status=200)


def classify_with_gemini(image_b64: str, mime_type: str, api_key: str) -> dict:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    prompt = (
        "Clasifica esta imagen en una de estas categorías: "
        "Documento, Foto, Factura, Diagrama, Captura de Pantalla, Otro. "
        "Responde SOLO con JSON válido sin markdown ni explicaciones: "
        '{"tipo_detectado": "<categoría>", "descripcion": "<descripción breve en español, máx 100 caracteres>"}'
    )
    payload = json.dumps({
        "contents": [{"parts": [
            {"inline_data": {"mime_type": mime_type, "data": image_b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {"maxOutputTokens": 200, "temperature": 0.1}
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if 'error' in data:
        raise ValueError(data['error'].get('message', 'Error Gemini'))

    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = text.replace("```json", "").replace("```", "").strip()
    result = json.loads(text)
    return {
        "tipo_detectado": result.get("tipo_detectado", "Otro"),
        "descripcion":    result.get("descripcion", "")
    }