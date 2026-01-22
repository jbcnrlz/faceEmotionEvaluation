# face_study/export_utils.py
import csv
import io
from django.http import HttpResponse
from decimal import Decimal
from datetime import datetime
import json

def export_ratings_to_csv(queryset=None, include_all_emotions=True):
    """
    Exporta avaliações para CSV com uma coluna para cada emoção
    e a URL da imagem na última coluna.
    """
    from .models import ImageRating, EmotionalState
    
    if queryset is None:
        queryset = ImageRating.objects.all()
    
    queryset = queryset.select_related(
        'participant', 'image'
    ).prefetch_related(
        'emotion_rankings__emotion'
    ).order_by('created_at')
    
    all_emotions = EmotionalState.objects.all().order_by('name')
    
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    
    # Cabeçalho
    headers = [
        'rating_id',
        'participant_email',
        'image_code',
        'image_filename',
        'rating_created_at',
    ]
    
    # Colunas para cada emoção
    emotion_columns = [f'emotion_{emotion.name.lower().replace(" ", "_")}' for emotion in all_emotions]
    headers.extend(emotion_columns)
    
    # URL da imagem como última coluna
    headers.append('image_url')
    
    writer.writerow(headers)
    
    for rating in queryset:
        emotion_values = {emotion.name: '' for emotion in all_emotions}
        
        for emotion_ranking in rating.emotion_rankings.all():
            emotion_values[emotion_ranking.emotion.name] = str(emotion_ranking.agreement_level)
        
        row = [
            str(rating.id),
            rating.participant.email,
            rating.image.code,
            rating.image.image.name.split('/')[-1],
            rating.created_at.isoformat(),
        ]
        
        for emotion in all_emotions:
            row.append(emotion_values[emotion.name])
        
        image_url = rating.image.image.url if rating.image.image else ''
        row.append(image_url)
        
        writer.writerow(row)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='text/csv')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="ratings_export_{timestamp}.csv"'
    
    return response