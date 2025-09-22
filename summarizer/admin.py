from django.contrib import admin
from .models import Document
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_filename', 'language_mode', 'doc_type', 'status', 'created_at')
    readonly_fields = ('created_at','updated_at')
