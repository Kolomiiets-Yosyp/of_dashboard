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


from django import forms
from django.contrib.auth.hashers import make_password
from .models import Users


class PasswordChangeForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirm New Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Passwords don't match")

        return cleaned_data


from django import forms
from django_select2.forms import Select2MultipleWidget, Select2Widget
from .models import Assistant, Tag


class AssistantForm(forms.ModelForm):
    class Meta:
        model = Assistant
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введіть ім\'я асистента'
            })
        }


class TagForm(forms.ModelForm):
    assistants = forms.ModelMultipleChoiceField(
        queryset=Assistant.objects.all(),
        widget=Select2MultipleWidget(attrs={
            'class': 'form-control',
            'data-placeholder': 'Оберіть асистентів'
        }),
        required=False
    )

    class Meta:
        model = Tag
        fields = ['name']
