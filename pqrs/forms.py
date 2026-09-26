from django import forms
from pqrs.models import PQRS


class PQRSCrearForm(forms.ModelForm):

    class Meta:
        model = PQRS
        fields = [
            'tipo',
            'nombre_completo',
            'email',
            'telefono',
            'documento_identidad',
            'asunto',
            'descripcion',
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Juan Carlos Pérez',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'correo@ejemplo.com',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+57 300 000 0000',
            }),
            'documento_identidad': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Número de cédula o NIT',
            }),
            'asunto': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Resuma brevemente su solicitud',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Describa detalladamente su solicitud...',
                'rows': 6,
            }),
        }

    def clean_nombre_completo(self):
        nombre = self.cleaned_data.get('nombre_completo', '').strip()
        if len(nombre) < 3:
            raise forms.ValidationError('Ingrese su nombre completo.')
        return nombre

    def clean_descripcion(self):
        desc = self.cleaned_data.get('descripcion', '').strip()
        if len(desc) < 20:
            raise forms.ValidationError(
                'La descripción debe tener al menos 20 caracteres.'
            )
        return desc


class PQRSConsultarForm(forms.Form):
    radicado = forms.CharField(
        max_length=20,
        label='Código de radicado',
        widget=forms.TextInput(attrs={
            'class': 'form-input consulta-input',
            'placeholder': 'Ej: PQR-202501-AB12CD',
            'autocomplete': 'off',
        }),
    )

    def clean_radicado(self):
        return self.cleaned_data['radicado'].strip().upper()