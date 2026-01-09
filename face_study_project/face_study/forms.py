from django import forms
from django.core.exceptions import ValidationError
from .models import EmotionalState, FaceImage, StudyConfiguration
from django.core.validators import EmailValidator

class ParticipantEmailForm(forms.Form):
    email = forms.EmailField(
        label="Seu e-mail",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'seu@email.com'
        })
    )

class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = FaceImage
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }

class EmotionRankingForm(forms.Form):
    def __init__(self, *args, **kwargs):
        emotions = kwargs.pop('emotions', [])
        super().__init__(*args, **kwargs)
        
        for i, emotion in enumerate(emotions):
            self.fields[f'emotion_{emotion.id}'] = forms.IntegerField(
                label=emotion.name,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'min': 1,
                    'max': len(emotions),
                    'style': 'width: 80px;'
                }),
                required=True
            )

class StudyConfigForm(forms.ModelForm):
    class Meta:
        model = StudyConfiguration
        fields = ['images_per_session', 'is_active']
        widgets = {
            'images_per_session': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }