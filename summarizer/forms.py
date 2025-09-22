from django import forms
from .models import Document, LANG_CHOICES, DOC_CHOICES

class UploadForm(forms.ModelForm):
    language_mode = forms.ChoiceField(choices=LANG_CHOICES, widget=forms.RadioSelect, initial='multi')
    doc_type = forms.ChoiceField(choices=DOC_CHOICES, initial='default')
    class Meta:
        model = Document
        fields = ['uploaded_file', 'language_mode', 'doc_type']
