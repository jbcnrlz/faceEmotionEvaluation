from django import forms
from .models import FaceImage, StudyConfiguration
from django.core.validators import FileExtensionValidator

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

class EmotionAgreementForm(forms.Form):
    def __init__(self, *args, **kwargs):
        emotions = kwargs.pop('emotions', [])
        super().__init__(*args, **kwargs)
        
        for emotion in emotions:
            self.fields[f'emotion_{emotion.id}'] = forms.DecimalField(
                label=emotion.name,
                min_value=0,
                max_value=1,
                decimal_places=2,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control agreement-input',
                    'min': '0',
                    'max': '1',
                    'step': '0.01',
                    'data-emotion-id': emotion.id,
                    'data-emotion-name': emotion.name,
                }),
                required=True,
                initial=0.5  # Valor padrão
            )


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
        fields = ['min_images_per_session', 'max_images_per_session', 'max_ratings_per_image', 'is_active']
        widgets = {
            'min_images_per_session': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'max_images_per_session': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'max_ratings_per_image': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        min_images = cleaned_data.get('min_images_per_session')
        max_images = cleaned_data.get('max_images_per_session')
        
        if min_images and max_images and min_images > max_images:
            raise forms.ValidationError(
                "Minimum images per session cannot be greater than maximum."
            )
        
        return cleaned_data