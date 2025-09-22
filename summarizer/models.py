import uuid, json
from django.db import models
from django.core.validators import FileExtensionValidator

LANG_CHOICES = [
    ('en', 'English'),
    ('multi', 'Multilingual'),
]
DOC_CHOICES = [
    ('default', 'Default'),
    ('labs', 'Labs (tables)'),
]
STATUS = [
    ('uploaded','Uploaded'),
    ('processed','Processed'),
    ('failed','Failed'),
]

class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_file = models.FileField(upload_to='uploads/', validators=[
        FileExtensionValidator(allowed_extensions=['pdf','png','jpg','jpeg','tiff','bmp','webp'])
    ])
    original_filename = models.CharField(max_length=255, blank=True)
    language_mode = models.CharField(max_length=10, choices=LANG_CHOICES, default='multi')
    doc_type = models.CharField(max_length=10, choices=DOC_CHOICES, default='default')
    status = models.CharField(max_length=10, choices=STATUS, default='uploaded')
    ocr_text = models.TextField(blank=True)
    summary_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.original_filename or self.uploaded_file.name}"
