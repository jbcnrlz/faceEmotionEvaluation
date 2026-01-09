from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import os

def image_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex[:16]}.{ext}"
    return f'faces/{filename}'

class EmotionalState(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class FaceImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to=image_upload_path)
    code = models.CharField(max_length=20, unique=True, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_rated = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"IMG-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.code} - {self.image.name}"

class Participant(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_sessions = models.IntegerField(default=0)
    
    def __str__(self):
        return self.email

class ImageRating(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ratings')
    image = models.ForeignKey(FaceImage, on_delete=models.CASCADE, related_name='ratings')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['participant', 'image']
    
    def __str__(self):
        return f"{self.participant.email} - {self.image.code}"

class EmotionRanking(models.Model):
    rating = models.ForeignKey(ImageRating, on_delete=models.CASCADE, related_name='emotion_rankings')
    emotion = models.ForeignKey(EmotionalState, on_delete=models.CASCADE)
    rank = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    class Meta:
        unique_together = ['rating', 'rank']
        ordering = ['rating', 'rank']
    
    def __str__(self):
        return f"Rank {self.rank}: {self.emotion.name}"

class StudyConfiguration(models.Model):
    images_per_session = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        # Garante que apenas uma configuração esteja ativa
        if self.is_active:
            StudyConfiguration.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Config: {self.images_per_session} imagens/sessão"