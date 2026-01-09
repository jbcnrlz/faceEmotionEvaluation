from django.contrib import admin
from .models import *

@admin.register(FaceImage)
class FaceImageAdmin(admin.ModelAdmin):
    list_display = ['code', 'image', 'is_rated', 'uploaded_at']
    list_filter = ['is_rated', 'uploaded_at']
    search_fields = ['code']

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['email', 'created_at', 'completed_sessions']
    search_fields = ['email']

@admin.register(ImageRating)
class ImageRatingAdmin(admin.ModelAdmin):
    list_display = ['participant', 'image', 'created_at']
    list_filter = ['created_at']

@admin.register(EmotionalState)
class EmotionalStateAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

admin.site.register(EmotionRanking)
admin.site.register(StudyConfiguration)