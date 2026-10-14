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

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Campo de arquivo que aceita vários arquivos e retorna uma lista."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            if not data:
                # Lista vazia: dispara o erro de campo obrigatório
                return [single_file_clean(None, initial)]
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)]


class MultipleImageUploadForm(forms.Form):
    """
    Upload de várias imagens de uma vez.

    Cada arquivo é validado individualmente: os válidos ficam em
    `valid_images` e os inválidos em `invalid_images` como (nome, erro).
    """
    images = MultipleFileField(
        label='Imagens',
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    def clean_images(self):
        files = self.cleaned_data['images']
        image_field = forms.ImageField()
        self.valid_images = []
        self.invalid_images = []

        for f in files:
            try:
                image_field.clean(f)
                self.valid_images.append(f)
            except forms.ValidationError as e:
                self.invalid_images.append((f.name, ' '.join(e.messages)))

        return files


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