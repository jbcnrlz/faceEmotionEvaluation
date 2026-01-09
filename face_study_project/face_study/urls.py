from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'faceStudy'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_image, name='upload_image'),
    path('start/', views.start_session, name='start_session'),
    path('rate/', views.rate_images, name='rate_images'),
    path('complete/', views.session_complete, name='session_complete'),
    path('emotions/', views.manage_emotional_states, name='manage_emotional_states'),
    path('emotions/delete/<int:emotion_id>/', views.delete_emotion, name='delete_emotion'),
    path('config/', views.study_config, name='study_config'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)