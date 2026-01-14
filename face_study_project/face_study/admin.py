from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from .models import *

@admin.register(FaceImage)
class FaceImageAdmin(admin.ModelAdmin):
    list_display = ['code', 'image_preview', 'uploaded_at', 'rating_count_display', 'is_available_display']
    list_filter = ['uploaded_at', 'ratings__participant']
    search_fields = ['code']
    readonly_fields = ['image_preview', 'code', 'uploaded_at', 'rating_count_display']
    fields = ['code', 'image', 'image_preview', 'uploaded_at', 'rating_count_display']
    actions = ['reset_ratings']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Preview'
    
    def rating_count_display(self, obj):
        count = obj.ratings.count()
        config = StudyConfiguration.objects.filter(is_active=True).first()
        if not config:
            config = StudyConfiguration.objects.create()
        
        max_ratings = config.max_ratings_per_image
        percentage = (count / max_ratings * 100) if max_ratings > 0 else 0
        
        # Cores baseadas no progresso
        if count >= max_ratings:
            color = 'danger'
            status = 'FULL'
        elif count >= max_ratings * 0.8:
            color = 'warning'
            status = 'HIGH'
        elif count > 0:
            color = 'info'
            status = 'PARTIAL'
        else:
            color = 'secondary'
            status = 'EMPTY'
        
        return format_html(
            '<span class="badge bg-{}">{} ({}/{})</span>',
            color, status, count, max_ratings
        )
    rating_count_display.short_description = 'Ratings'
    
    def is_available_display(self, obj):
        config = StudyConfiguration.objects.filter(is_active=True).first()
        if not config:
            config = StudyConfiguration.objects.create()
        
        if obj.ratings.count() >= config.max_ratings_per_image:
            return format_html('<span class="badge bg-danger">Unavailable</span>')
        else:
            return format_html('<span class="badge bg-success">Available</span>')
    is_available_display.short_description = 'Availability'
    
    def reset_ratings(self, request, queryset):
        """Ação para resetar as avaliações de imagens selecionadas"""
        count = 0
        for image in queryset:
            # Remove todas as avaliações desta imagem
            deleted_count, _ = ImageRating.objects.filter(image=image).delete()
            count += 1
        
        self.message_user(
            request, 
            f'Successfully reset ratings for {count} image(s).'
        )
    reset_ratings.short_description = 'Reset ratings for selected images'

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['email', 'created_at', 'last_session_at', 'total_ratings', 'unique_images_rated']
    search_fields = ['email']
    readonly_fields = ['created_at', 'last_session_at', 'total_ratings_display', 'unique_images_display']
    list_filter = ['created_at', 'last_session_at']
    
    def total_ratings(self, obj):
        return obj.ratings.count()
    total_ratings.short_description = 'Total Ratings'
    
    def unique_images_rated(self, obj):
        return obj.ratings.values('image').distinct().count()
    unique_images_rated.short_description = 'Unique Images'
    
    def total_ratings_display(self, obj):
        return obj.total_ratings_count()
    total_ratings_display.short_description = 'Total Ratings'
    
    def unique_images_display(self, obj):
        return obj.rated_images_count()
    unique_images_display.short_description = 'Unique Images Rated'
    
    # Adicionar ação para ver detalhes das avaliações
    actions = ['view_ratings_details']
    
    def view_ratings_details(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one participant.', level='error')
            return
        
        participant = queryset.first()
        # Redirecionar para uma view de detalhes (você pode criar depois)
        from django.urls import reverse
        url = reverse('admin:face_study_imagerating_changelist') + f'?participant__id__exact={participant.id}'
        return HttpResponseRedirect(url)
    view_ratings_details.short_description = 'View ratings details'

@admin.register(ImageRating)
class ImageRatingAdmin(admin.ModelAdmin):
    list_display = ['participant', 'image', 'created_at', 'emotion_rankings_count']
    list_filter = ['created_at', 'participant']
    search_fields = ['participant__email', 'image__code']
    
    def emotion_rankings_count(self, obj):
        return obj.emotion_rankings.count()
    emotion_rankings_count.short_description = 'Emotions Ranked'

@admin.register(EmotionalState)
class EmotionalStateAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'usage_count']
    search_fields = ['name']
    
    def usage_count(self, obj):
        return obj.emotionranking_set.count()
    usage_count.short_description = 'Times Used'

@admin.register(EmotionRanking)
class EmotionRankingAdmin(admin.ModelAdmin):
    list_display = ['rating', 'emotion', 'agreement_level', 'created_at']
    list_filter = ['emotion', 'agreement_level']
    search_fields = ['emotion__name', 'rating__participant__email']
    list_editable = ['agreement_level']

@admin.register(StudyConfiguration)
class StudyConfigurationAdmin(admin.ModelAdmin):
    list_display = ['min_images_per_session', 'max_images_per_session', 'max_ratings_per_image', 'is_active', 'created_at']
    list_editable = ['is_active']
    list_filter = ['is_active']
    readonly_fields = ['created_at']
    
    def save_model(self, request, obj, form, change):
        # Garante que apenas uma configuração esteja ativa
        if obj.is_active:
            StudyConfiguration.objects.filter(is_active=True).update(is_active=False)
        super().save_model(request, obj, form, change)