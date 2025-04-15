from django import forms
from .models import Users

class UserForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['login', 'password']
        widgets = {
            'login': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введіть логін'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введіть пароль'}),
        }
