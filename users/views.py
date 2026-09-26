# Python Standard Library

# Third-party Libraries
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import generic
from rest_framework.authtoken.models import Token

# Local Modules
from core import views as core_views
from users import forms
from users import models


class DeleteUserDataView(generic.FormView):
    form_class = forms.DeleteUserDataForm
    template_name = 'users/delete_user_data.html'
    success_url = reverse_lazy('users:delete_user_data')

    def get_initial(self):
        initial = super().get_initial()
        email = self.request.session.get('email')
        if email:
            initial['email'] = email
        return initial

    def form_valid(self, form):

        if 'email' in self.request.session:
            email = self.request.session.get('email')
            code = form.cleaned_data.get('code')
            user = models.User.objects.filter(email=email).first()
            if not user:
                messages.error(
                    self.request,
                    'No existe un usuario con el correo ingresado'
                )
                del self.request.session['email']
                return self.form_invalid(form)

            verification_code = models.UserVerificationCode.objects.filter(
                user=user, code=code
            ).first()
            if not verification_code:
                messages.error(
                    self.request,
                    'Código inválido'
                )
                return self.form_invalid(form)

            if verification_code.valid_until < timezone.now():
                messages.error(
                    self.request,
                    'Código expirado, por favor solicite un nuevo código'
                )
                del self.request.session['email']
                return self.form_invalid(form)

            Token.objects.filter(user=user).delete()
            models.UserVerificationCode.objects.filter(user=user).delete()
            models.UserLevel.objects.filter(user=user).delete()
            user.delete()

            del self.request.session['email']
            messages.success(self.request, 'Cuenta eliminada exitosamente')

        else:
            email = form.cleaned_data.get('email')
            user = models.User.objects.filter(email=email).first()
            if not user:
                messages.error(
                    self.request,
                    'No existe un usuario con el correo ingresado'
                )
                return self.form_invalid(form)

            core_views.verification_email_delete_user(user)
            self.request.session['email'] = email

        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            if 'clear_email' in request.POST:
                del request.session['email']
                return redirect('users:delete_user_data')
            else:
                return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'email' in self.request.session:
            context['email'] = self.request.session.get('email')
        return context
