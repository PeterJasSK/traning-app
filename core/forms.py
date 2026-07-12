from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser, Measurement, Goal, Message

# --- Login formulár ---
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Login',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='Heslo',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

# --- Merania ---
class MeasurementForm(forms.ModelForm):
    class Meta:
        model = Measurement
        fields = [
            'date', 'weight', 'height', 'chest', 'waist',
            'biceps', 'thigh', 'calf', 'photo', 'note'
        ]

# --- Ciele ---
class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['description', 'target_date']

# --- Správy v chate ---
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Napíš správu...'
            }),
        }

# --- Formulár pre trénera: pridať zverenca ---
class AddTraineeForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Heslo'}),
        required=True
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'trainee'  # automaticky nastavíme rolu
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

# --- Formulár pre úpravu zverenca ---
class EditTraineeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email']  # len základné údaje

# --- Formulár pre pridanie trénera ---
class AddTrainerForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Heslo'}),
        required=True
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'trainer'  # automaticky nastavíme rolu
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
