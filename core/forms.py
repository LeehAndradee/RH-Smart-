from django import forms
from .models import Falta

class FaltaForm(forms.ModelForm):
    class Meta:
        model = Falta
        fields = ['data', 'documento', 'observacao']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'documento': forms.FileInput(attrs={'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }