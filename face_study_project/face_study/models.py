from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import os
from decimal import Decimal

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
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"IMG-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def rating_count(self):
        """Retorna quantas vezes esta imagem foi avaliada"""
        return self.ratings.count()
    
    def is_available_for_rating(self, config=None):
        """Verifica se a imagem está disponível para avaliação"""
        if not config:
            config = StudyConfiguration.objects.filter(is_active=True).first()
            if not config:
                config = StudyConfiguration.objects.create()
        
        return self.ratings.count() < config.max_ratings_per_image
    
    def get_availability_status(self):
        """Retorna status de disponibilidade para o admin"""
        config = StudyConfiguration.objects.filter(is_active=True).first()
        if not config:
            config = StudyConfiguration.objects.create()
        
        count = self.rating_count()
        max_allowed = config.max_ratings_per_image
        
        if count >= max_allowed:
            return f"FULL ({count}/{max_allowed})"
        elif count > 0:
            return f"PARTIAL ({count}/{max_allowed})"
        else:
            return f"EMPTY (0/{max_allowed})"
    
    def __str__(self):
        return f"{self.code} - {self.image.name}"
    
class Participant(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Removemos completed_sessions pois agora pode fazer múltiplas sessões
    last_session_at = models.DateTimeField(null=True, blank=True)
    
    def total_ratings_count(self):
        """Retorna o total de avaliações deste participante"""
        return self.ratings.count()
    
    def rated_images_count(self):
        """Retorna quantas imagens únicas este participante avaliou"""
        return self.ratings.values('image').distinct().count()
    
    def __str__(self):
        return f"{self.email} ({self.ratings.count()} ratings)"
    
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
    agreement_level = models.DecimalField(
        max_digits=3,  # 0.00 a 1.00
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('1.00'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['rating', 'emotion']  # Cada emoção só pode ser avaliada uma vez por rating
        ordering = ['emotion__name']
    
    def __str__(self):
        return f"{self.emotion.name}: {self.agreement_level}"

class StudyConfiguration(models.Model):
    min_images_per_session = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        verbose_name="Minimum images per session"
    )
    max_images_per_session = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        verbose_name="Maximum images per session"
    )
    max_ratings_per_image = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Maximum ratings per image",
        help_text="Maximum number of times an image can be rated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        # Garante que apenas uma configuração esteja ativa
        if self.is_active:
            StudyConfiguration.objects.filter(is_active=True).update(is_active=False)
        
        # Valida que min <= max
        if self.min_images_per_session > self.max_images_per_session:
            self.min_images_per_session = self.max_images_per_session
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Config: {self.min_images_per_session}-{self.max_images_per_session} images, max {self.max_ratings_per_image} ratings/image"