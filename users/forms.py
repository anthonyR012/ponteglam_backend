# Python Standard Library

# Third-party Libraries
from django import forms

# Local Modules
from users.models import User


class DeleteUserDataForm(forms.ModelForm):

    code = forms.CharField(
        max_length=5, required=False
    )

    class Meta:
        model = User
        fields = ('email', )
