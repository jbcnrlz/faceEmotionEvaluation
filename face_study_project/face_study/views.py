from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.paginator import Paginator
from django.conf import settings
import json
from django.contrib.auth.decorators import login_required
import random
from .models import *
from .forms import *
from django.db.models import Count

@login_required
def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save()
            messages.success(request, f'Imagem enviada! Código: {image.code}')
            return redirect('faceStudy:upload_image')
    else:
        form = ImageUploadForm()
    
    images = FaceImage.objects.all().order_by('-uploaded_at')
    return render(request, 'studyInterfaces/upload.html', {
        'form': form,
        'images': images
    })

def start_session(request):
    if request.method == 'POST':
        form = ParticipantEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Verifica se usuário já completou uma sessão
            participant, created = Participant.objects.get_or_create(email=email)
            
            if participant.completed_sessions > 0:
                messages.warning(request, 'Este e-mail já participou do estudo.')
                return render(request, 'studyInterfaces/start_session.html', {
                    'form': form,
                    'study_config': StudyConfiguration.objects.filter(is_active=True).first()
                })
            
            # Obtém configuração ativa
            config = StudyConfiguration.objects.filter(is_active=True).first()
            if not config:
                config = StudyConfiguration.objects.create()
            
            # Gera número aleatório de imagens para esta sessão
            images_for_this_session = random.randint(
                config.min_images_per_session, 
                config.max_images_per_session
            )
            
            # Inicia sessão com número aleatório de imagens
            request.session['participant_email'] = email
            request.session['session_active'] = True
            request.session['rated_images'] = []
            request.session['session_image_count'] = images_for_this_session
            request.session['session_min_images'] = config.min_images_per_session
            request.session['session_max_images'] = config.max_images_per_session
            
            return redirect('faceStudy:rate_images')
    else:
        form = ParticipantEmailForm()
    
    # Obtém configuração ativa para mostrar informações
    study_config = StudyConfiguration.objects.filter(is_active=True).first()
    if not study_config:
        # Cria configuração padrão se não existir
        study_config = StudyConfiguration.objects.create()
    
    return render(request, 'studyInterfaces/start_session.html', {
        'form': form,
        'study_config': study_config
    })

def rate_images(request):
    if not request.session.get('session_active'):
        return redirect('faceStudy:start_session')
    
    email = request.session.get('participant_email')
    if not email:
        return redirect('faceStudy:start_session')
    
    participant = get_object_or_404(Participant, email=email)
    
    # Obtém configuração ativa
    config = StudyConfiguration.objects.filter(is_active=True).first()
    if not config:
        config = StudyConfiguration.objects.create()
    
    # Obtém número de imagens para esta sessão (armazenado na sessão)
    session_image_count = request.session.get('session_image_count', 10)
    
    # Obter todas as emoções para o formulário
    emotions = EmotionalState.objects.all().order_by('name')
    
    if request.method == 'POST':
        image_id = request.POST.get('image_id')
        image = get_object_or_404(FaceImage, id=image_id)
        
        with transaction.atomic():
            # Cria avaliação
            rating = ImageRating.objects.create(
                participant=participant,
                image=image
            )
            
            # Processa rankings
            for emotion in emotions:
                rank_key = f'emotion_{emotion.id}'
                rank_value = request.POST.get(rank_key)
                if rank_value:
                    EmotionRanking.objects.create(
                        rating=rating,
                        emotion=emotion,
                        rank=int(rank_value)
                    )
            
            # NÃO marcar imagem como avaliada globalmente
            # O controle agora é feito pela contagem de ratings
            
            # Atualiza sessão
            rated = request.session.get('rated_images', [])
            rated.append(str(image.id))
            request.session['rated_images'] = rated
            
            # Verifica se completou a sessão
            if len(rated) >= session_image_count:
                participant.completed_sessions += 1
                participant.save()
                request.session['session_active'] = False
                return redirect('faceStudy:session_complete')
            
            return redirect('faceStudy:rate_images')
    
    # Pega as imagens já avaliadas nesta sessão
    rated_ids = request.session.get('rated_images', [])
    
    # Se já avaliou todas as imagens da sessão
    if len(rated_ids) >= session_image_count:
        participant.completed_sessions += 1
        participant.save()
        request.session['session_active'] = False
        return redirect('faceStudy:session_complete')
    
    # Busca a próxima imagem disponível
    # 1. Imagens que ainda não atingiram o limite máximo de avaliações
    # 2. Exclui imagens que este participante já avaliou
    # 3. Exclui imagens já avaliadas nesta sessão
    
    # Annota cada imagem com a contagem de ratings
    current_image = FaceImage.objects.annotate(
        rating_count=Count('ratings')
    ).filter(
        rating_count__lt=config.max_ratings_per_image  # Ainda não atingiu o limite
    ).exclude(
        id__in=ImageRating.objects.filter(
            participant=participant
        ).values_list('image_id', flat=True)
    ).exclude(
        id__in=[uuid.UUID(id) for id in rated_ids]
    ).order_by('?').first()
    
    if not current_image:
        # Não há mais imagens disponíveis para este participante
        participant.completed_sessions += 1
        participant.save()
        request.session['session_active'] = False
        return redirect('faceStudy:session_complete')
    
    # Calcular o progresso da imagem
    image_rating_count = current_image.ratings.count()
    image_rating_progress = (image_rating_count / config.max_ratings_per_image) * 100
    
    form = EmotionRankingForm(emotions=emotions)
    
    return render(request, 'studyInterfaces/rate_images.html', {
        'image': current_image,
        'emotions': emotions,
        'form': form,
        'config': config,
        'image_rating_info': {
            'current_count': image_rating_count,
            'max_allowed': config.max_ratings_per_image,
            'progress_percent': image_rating_progress,
            'remaining': config.max_ratings_per_image - image_rating_count
        },
        'progress': {
            'current': len(rated_ids) + 1,
            'total': session_image_count,
            'min_images': request.session.get('session_min_images', 1),
            'max_images': request.session.get('session_max_images', 10),
            'estimated_time': session_image_count * 2,
        }
    })

def session_complete(request):
    if 'participant_email' in request.session:
        del request.session['participant_email']
    if 'session_active' in request.session:
        del request.session['session_active']
    if 'rated_images' in request.session:
        del request.session['rated_images']
    
    return render(request, 'studyInterfaces/session_complete.html')

@login_required
def manage_emotional_states(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            EmotionalState.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            messages.success(request, 'Estado emocional adicionado!')
        return redirect('faceStudy:manage_emotional_states')
    
    emotions = EmotionalState.objects.all()
    return render(request, 'studyInterfaces/manage_emotions.html', {'emotions': emotions})

@login_required
def delete_emotion(request, emotion_id):
    emotion = get_object_or_404(EmotionalState, id=emotion_id)
    emotion.delete()
    messages.success(request, 'Estado emocional removido!')
    return redirect('faceStudy:manage_emotional_states')

@login_required
def study_config(request):
    config = StudyConfiguration.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        form = StudyConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuração atualizada!')
            return redirect('faceStudy:study_config')
    else:
        form = StudyConfigForm(instance=config)
    
    return render(request, 'studyInterfaces/study_config.html', {'form': form})

@login_required
def dashboard(request):
    stats = {
        'total_images': FaceImage.objects.count(),
        'rated_images': FaceImage.objects.filter(is_rated=True).count(),
        'total_participants': Participant.objects.count(),
        'total_ratings': ImageRating.objects.count(),
        'emotional_states': EmotionalState.objects.count(),
    }
    
    recent_ratings = ImageRating.objects.select_related(
        'participant', 'image'
    ).order_by('-created_at')[:10]
    
    return render(request, 'studyInterfaces/dashboard.html', {
        'stats': stats,
        'recent_ratings': recent_ratings
    })