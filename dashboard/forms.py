from django import forms
from .models import Users

class UserForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['name', 'login', 'password']  # ➕ додали name
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Введіть ім'я"}),
            'login': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введіть логін'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введіть пароль'}),
        }
