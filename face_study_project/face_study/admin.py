# face_study/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from .models import *
from .export_utils import export_ratings_to_csv
from .views import export_advanced

@admin.register(FaceImage)
class FaceImageAdmin(admin.ModelAdmin):
    list_display = ['code', 'image_preview', 'uploaded_at', 'rating_count_display', 'is_available_display']
    list_filter = ['uploaded_at', 'ratings__participant']
    search_fields = ['code']
    readonly_fields = ['image_preview', 'code', 'uploaded_at', 'rating_count_display']
    fields = ['code', 'image', 'image_preview', 'uploaded_at', 'rating_count_display']
    actions = ['reset_ratings', 'export_ratings_for_selected_images']
    
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
        
        if count >= max_ratings:
            color = 'red'
            status = 'FULL'
        elif count >= max_ratings * 0.8:
            color = 'orange'
            status = 'HIGH'
        elif count > 0:
            color = 'blue'
            status = 'PARTIAL'
        else:
            color = 'gray'
            status = 'EMPTY'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} ({}/{})</span>',
            color, status, count, max_ratings
        )
    rating_count_display.short_description = 'Ratings'
    
    def is_available_display(self, obj):
        config = StudyConfiguration.objects.filter(is_active=True).first()
        if not config:
            config = StudyConfiguration.objects.create()
        
        if obj.ratings.count() >= config.max_ratings_per_image:
            return format_html('<span style="color: red;">✗ Unavailable</span>')
        else:
            return format_html('<span style="color: green;">✓ Available</span>')
    is_available_display.short_description = 'Availability'
    
    def reset_ratings(self, request, queryset):
        """Ação para resetar as avaliações de imagens selecionadas"""
        count = 0
        for image in queryset:
            deleted_count, _ = ImageRating.objects.filter(image=image).delete()
            count += 1
        
        self.message_user(
            request, 
            f'Successfully reset ratings for {count} image(s).'
        )
    reset_ratings.short_description = 'Reset ratings for selected images'
    
    def export_ratings_for_selected_images(self, request, queryset):
        """Exporta avaliações das imagens selecionadas para CSV"""
        from .models import ImageRating
        ratings = ImageRating.objects.filter(image__in=queryset)
        return export_ratings_to_csv(ratings)
    export_ratings_for_selected_images.short_description = 'Export ratings for selected images (CSV)'


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['email', 'created_at', 'last_session_at', 'total_ratings', 'unique_images_rated']
    search_fields = ['email']
    readonly_fields = ['created_at', 'last_session_at', 'total_ratings_display', 'unique_images_display']
    list_filter = ['created_at', 'last_session_at']
    actions = ['export_ratings_for_selected_participants']
    
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
    
    def export_ratings_for_selected_participants(self, request, queryset):
        """Exporta avaliações dos participantes selecionados para CSV"""
        from .models import ImageRating
        ratings = ImageRating.objects.filter(participant__in=queryset)
        return export_ratings_to_csv(ratings)
    export_ratings_for_selected_participants.short_description = 'Export ratings for selected participants (CSV)'


@admin.register(ImageRating)
class ImageRatingAdmin(admin.ModelAdmin):
    list_display = ['participant', 'image', 'created_at', 'emotion_rankings_count']
    list_filter = ['created_at', 'participant']
    search_fields = ['participant__email', 'image__code']
    actions = ['export_selected_ratings_csv', 'export_all_ratings_csv']
    
    def emotion_rankings_count(self, obj):
        return obj.emotion_rankings.count()
    emotion_rankings_count.short_description = 'Emotions Ranked'
    
    def export_selected_ratings_csv(self, request, queryset):
        """Exporta avaliações selecionadas para CSV"""
        return export_ratings_to_csv(queryset)
    export_selected_ratings_csv.short_description = 'Export selected ratings to CSV'
    
    def export_all_ratings_csv(self, request, queryset):
        """Exporta TODAS as avaliações para CSV"""
        return export_ratings_to_csv()
    
    export_all_ratings_csv.short_description = 'Export ALL ratings to CSV'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [            
            path('export-advanced/', 
                    self.admin_site.admin_view(export_advanced), 
                    name='face_study_export_advanced'),
        ]
        return custom_urls + urls


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
        if obj.is_active:
            StudyConfiguration.objects.filter(is_active=True).update(is_active=False)
        super().save_model(request, obj, form, change)