from django.utils import timezone
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
            
            # Cria ou obtém o participante
            participant, created = Participant.objects.get_or_create(email=email)
            
            # Atualiza o timestamp da última sessão
            participant.last_session_at = timezone.now()
            participant.save()
            
            # Obtém configuração ativa
            config = StudyConfiguration.objects.filter(is_active=True).first()
            if not config:
                config = StudyConfiguration.objects.create()
            
            # Gera número aleatório de imagens para esta sessão
            images_for_this_session = random.randint(
                config.min_images_per_session, 
                config.max_images_per_session
            )
            
            # Inicia sessão
            request.session['participant_email'] = email
            request.session['session_active'] = True
            request.session['rated_images'] = []  # Imagens avaliadas nesta sessão
            request.session['session_image_count'] = images_for_this_session
            request.session['session_min_images'] = config.min_images_per_session
            request.session['session_max_images'] = config.max_images_per_session
            request.session['participant_id'] = str(participant.id)  # Armazena ID do participante
            
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
    participant_id = request.session.get('participant_id')
    
    if not email or not participant_id:
        return redirect('faceStudy:start_session')
    
    try:
        participant = Participant.objects.get(id=participant_id, email=email)
    except Participant.DoesNotExist:
        # Se não encontrar, redireciona para começar nova sessão
        return redirect('faceStudy:start_session')
    
    # Obtém configuração ativa
    config = StudyConfiguration.objects.filter(is_active=True).first()
    if not config:
        config = StudyConfiguration.objects.create()
    
    # Obtém número de imagens para esta sessão
    session_image_count = request.session.get('session_image_count', 10)
    
    # Obter todas as emoções para o formulário
    emotions = EmotionalState.objects.all().order_by('name')
    
    if request.method == 'POST':
        image_id = request.POST.get('image_id')
        image = get_object_or_404(FaceImage, id=image_id)
        
        with transaction.atomic():
            # Verifica se o participante já avaliou esta imagem
            existing_rating = ImageRating.objects.filter(
                participant=participant,
                image=image
            ).first()
            
            if existing_rating:
                # Se já avaliou, atualiza os rankings
                # Remove rankings antigos
                existing_rating.emotion_rankings.all().delete()
                
                # Adiciona novos rankings
                for emotion in emotions:
                    agreement_key = f'emotion_{emotion.id}'
                    agreement_value = request.POST.get(agreement_key)
                    if agreement_value:
                        try:
                            agreement_decimal = Decimal(agreement_value)
                            if agreement_decimal < Decimal('0.00'):
                                agreement_decimal = Decimal('0.00')
                            elif agreement_decimal > Decimal('1.00'):
                                agreement_decimal = Decimal('1.00')
                            
                            agreement_decimal = agreement_decimal.quantize(Decimal('0.01'))
                            
                            EmotionRanking.objects.create(
                                rating=existing_rating,
                                emotion=emotion,
                                agreement_level=agreement_decimal
                            )
                        except:
                            pass
            else:
                # Se não avaliou, cria nova avaliação
                rating = ImageRating.objects.create(
                    participant=participant,
                    image=image
                )
                
                # Processa níveis de concordância
                for emotion in emotions:
                    agreement_key = f'emotion_{emotion.id}'
                    agreement_value = request.POST.get(agreement_key)
                    if agreement_value:
                        try:
                            agreement_decimal = Decimal(agreement_value)
                            if agreement_decimal < Decimal('0.00'):
                                agreement_decimal = Decimal('0.00')
                            elif agreement_decimal > Decimal('1.00'):
                                agreement_decimal = Decimal('1.00')
                            
                            agreement_decimal = agreement_decimal.quantize(Decimal('0.01'))
                            
                            EmotionRanking.objects.create(
                                rating=rating,
                                emotion=emotion,
                                agreement_level=agreement_decimal
                            )
                        except:
                            pass
        
        # Atualiza sessão
        rated = request.session.get('rated_images', [])
        rated.append(str(image.id))
        request.session['rated_images'] = rated
        
        # Verifica se completou a sessão
        if len(rated) >= session_image_count:
            request.session['session_active'] = False
            return redirect('faceStudy:session_complete')
        
        return redirect('faceStudy:rate_images')
    
    # Pega as imagens já avaliadas nesta sessão
    rated_in_this_session = request.session.get('rated_images', [])
    
    # Se já avaliou todas as imagens da sessão
    if len(rated_in_this_session) >= session_image_count:
        request.session['session_active'] = False
        return redirect('faceStudy:session_complete')
    
    # Busca a próxima imagem disponível para este participante
    # 1. Imagens que ainda não atingiram o limite máximo de avaliações
    # 2. Exclui imagens que este participante já avaliou (em qualquer sessão)
    # 3. Exclui imagens já avaliadas nesta sessão
    
    # Imagens que o participante já avaliou (em qualquer sessão)
    already_rated_by_participant = ImageRating.objects.filter(
        participant=participant
    ).values_list('image_id', flat=True)
    
    # Busca próxima imagem
    current_image = FaceImage.objects.annotate(
        rating_count=Count('ratings')
    ).filter(
        rating_count__lt=config.max_ratings_per_image  # Ainda não atingiu o limite
    ).exclude(
        id__in=already_rated_by_participant  # Exclui imagens já avaliadas pelo participante
    ).exclude(
        id__in=[uuid.UUID(id) for id in rated_in_this_session]  # Exclui imagens já avaliadas nesta sessão
    ).order_by('?').first()
    
    if not current_image:
        # Não há mais imagens disponíveis para este participante
        request.session['session_active'] = False
        return redirect('faceStudy:session_complete')
    
    # Verifica se há uma avaliação anterior desta imagem por este participante
    previous_rating = ImageRating.objects.filter(
        participant=participant,
        image=current_image
    ).first()
    
    # Calcular estatísticas da imagem
    image_rating_count = current_image.ratings.count()
    image_rating_progress = (image_rating_count / config.max_ratings_per_image) * 100
    
    # Cria o formulário de concordância com valores anteriores se existirem
    form = EmotionAgreementForm(emotions=emotions)
    
    # Se houver avaliação anterior, preenche o formulário com esses valores
    if previous_rating:
        initial_data = {}
        for ranking in previous_rating.emotion_rankings.all():
            initial_data[f'emotion_{ranking.emotion.id}'] = str(ranking.agreement_level)
        form = EmotionAgreementForm(emotions=emotions, initial=initial_data)
    
    return render(request, 'studyInterfaces/rate_images.html', {
        'image': current_image,
        'emotions': emotions,
        'form': form,
        'config': config,
        'has_previous_rating': previous_rating is not None,
        'image_rating_info': {
            'current_count': image_rating_count,
            'max_allowed': config.max_ratings_per_image,
            'progress_percent': image_rating_progress,
            'remaining': config.max_ratings_per_image - image_rating_count
        },
        'progress': {
            'current': len(rated_in_this_session) + 1,
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