import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import FaceImage

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def make_image(name='face.png', color=(200, 100, 50)):
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), color).save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class MultipleImageUploadTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user('tester', password='pass')
        self.client.login(username='tester', password='pass')
        self.url = reverse('faceStudy:upload_image')

    def test_upload_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'multiple')

    def test_upload_multiple_images(self):
        files = [make_image(f'face_{i}.png') for i in range(5)]
        response = self.client.post(self.url, {'images': files})
        self.assertRedirects(response, self.url)
        self.assertEqual(FaceImage.objects.count(), 5)
        self.assertEqual(FaceImage.objects.values('code').distinct().count(), 5)

    def test_upload_400_images_in_single_request(self):
        files = [make_image(f'face_{i}.png') for i in range(400)]
        response = self.client.post(
            self.url, {'images': files}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['created'], 400)
        self.assertEqual(response.json()['errors'], [])
        self.assertEqual(FaceImage.objects.count(), 400)

    def test_invalid_files_are_reported_and_valid_ones_saved(self):
        files = [
            make_image('ok1.png'),
            SimpleUploadedFile('broken.png', b'not an image', content_type='image/png'),
            make_image('ok2.png'),
        ]
        response = self.client.post(
            self.url, {'images': files}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        data = response.json()
        self.assertEqual(data['created'], 2)
        self.assertEqual(len(data['errors']), 1)
        self.assertEqual(data['errors'][0]['name'], 'broken.png')
        self.assertEqual(FaceImage.objects.count(), 2)

    def test_post_without_files_returns_error(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FaceImage.objects.count(), 0)

    def test_login_required(self):
        self.client.logout()
        response = self.client.post(self.url, {'images': [make_image()]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FaceImage.objects.count(), 0)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class FaceImageAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')

    def test_changelist_renders_with_content(self):
        FaceImage.objects.create(image=make_image('admin_face.png'))
        response = self.client.get(reverse('admin:face_study_faceimage_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'IMG-')
        self.assertContains(response, reverse('faceStudy:upload_image'))

    def test_changelist_empty_renders(self):
        response = self.client.get(reverse('admin:face_study_faceimage_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload de várias imagens')
