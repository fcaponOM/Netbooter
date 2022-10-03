from django import forms
from imageserver.httpserver.models import Image

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ('image', 'pub_date', 'os', 'version', 'size')