from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.forms import TextInput,EmailInput


class SignUpForm(forms.ModelForm):
    
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': "w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"}))

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password']
        widgets = {
            'username': TextInput(attrs={'class': "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"}),
            'email' : EmailInput(attrs={'class': "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"})
        }

    def save(self, commit=True):
        user = super().save(commit=False) #dont save to db yet
        user.set_password(self.cleaned_data['password']) #hashes pass
        if commit: #save to db
            user.save()
        return user
