import json
import urllib.request
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
    """Render the main frontend page."""
    lambda_url = getattr(settings, 'LAMBDA_URL', '')
    return render(request, 'catalogo/index.html', {'lambda_url': lambda_url})


@api_view(['POST'])
def classify_local(request):
    """
    Clasifica una imagen usando Gemini 1.5 Flash (gratuito).
    POST body: { "image_b64": "<base64>", "filename": "file.jpg" }
    """
    image_b64 = request.data.get('image_b64', '')

    if not image_b64:
        return Response({'error': 'image_b64 required'}, status=400)

    try:
        result = classify_with_gemini(image_b64)
        return Response(result)
    except Exception as e:
        return Response({
            'tipo_detectado': 'Desconocido',
            'descripcion': f'No se pudo clasificar: {str(e)}'
        }, status=200)


def classify_with_gemini(image_b64: str) -> dict:
    """
    Llama a Gemini 1.5 Flash (tier gratuito) para clasificar la imagen.
    Docs: https://ai.google.dev/api/generate-content
    """
    api_key = settings.GEMINI_API_KEY
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={api_key}"
    )

    prompt = (
        "Clasifica esta imagen en una de estas categorías: "
        "Documento, Foto, Factura, Diagrama, Captura de Pantalla, Otro. "
        "Responde SOLO con JSON válido sin markdown ni explicaciones: "
        '{"tipo_detectado": "<categoría>", "descripcion": "<descripción breve en español, máx 100 caracteres>"}'
    )

    payload = json.dumps({
        "contents": [{
            "parts": [
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_b64
                    }
                },
                {"text": prompt}
            ]
        }],
        "generationConfig": {
            "maxOutputTokens": 200,
            "temperature": 0.1
        }
    }).encode("utf-8")

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

    return {
        "tipo_detectado": result.get("tipo_detectado", "Otro"),
        "descripcion":    result.get("descripcion", "")
    }