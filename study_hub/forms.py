from django import forms
from .models import SubjectDocument

class SubjectDocumentForm(forms.ModelForm):
    class Meta:
        model = SubjectDocument
        fields = ['course', 'title', 'file']
        widgets = {
            'course': forms.Select(attrs={'class': 'w-full rounded-lg border-slate-200 text-sm focus:ring-indigo-500 focus:border-indigo-500'}),
            'title': forms.TextInput(attrs={'class': 'flex-1 rounded-lg border-slate-200 text-sm focus:ring-indigo-500 focus:border-indigo-500', 'placeholder': 'Document Title'}),
            'file': forms.FileInput(attrs={'class': 'text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'}),
        }
