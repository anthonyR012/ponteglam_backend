from django.views.generic import FormView, TemplateView
from django.urls import reverse_lazy

from pqrs.forms import PQRSCrearForm, PQRSConsultarForm
from pqrs.services import crear_pqrs, consultar_por_radicado


class PQRSHomeView(TemplateView):
    """Página de inicio del módulo PQRS — acceso público."""
    template_name = 'pqrs/home.html'


class PQRSCrearView(FormView):
    """
    Permite al ciudadano radicar una nueva PQRS sin autenticación.
    Al completarse con éxito, redirige al detalle con el radicado generado.
    """
    template_name = 'pqrs/crear.html'
    form_class = PQRSCrearForm

    def form_valid(self, form):
        pqrs = crear_pqrs(form.cleaned_data)
        # Guardamos el radicado en sesión para mostrarlo en la confirmación
        self.request.session['ultimo_radicado'] = pqrs.radicado
        from django.urls import reverse
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(
            reverse('pqrs:confirmacion', kwargs={'radicado': pqrs.radicado})
        )


class PQRSConfirmacionView(TemplateView):
    """Muestra el radicado generado tras crear una PQRS exitosamente."""
    template_name = 'pqrs/confirmacion.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        radicado = self.kwargs.get('radicado')
        from .services import consultar_por_radicado
        ctx['pqrs'] = consultar_por_radicado(radicado)
        return ctx


class PQRSConsultarView(FormView):
    """
    Vista pública para que el ciudadano consulte el estado
    de su PQRS ingresando el código de radicado.
    """
    template_name = 'pqrs/consultar.html'
    form_class = PQRSConsultarForm
    # Se renderiza en la misma vista; no redirigimos para conservar el contexto
    success_url = reverse_lazy('pqrs:consultar')

    def form_valid(self, form):
        radicado = form.cleaned_data['radicado']
        pqrs = consultar_por_radicado(radicado)
        return self.render_to_response(
            self.get_context_data(form=form, pqrs=pqrs, buscado=True)
        )


class PQRSDetalleView(TemplateView):
    """Detalle completo de una PQRS accesible por su radicado."""
    template_name = 'pqrs/detalle.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pqrs'] = consultar_por_radicado(self.kwargs['radicado'])
        return ctx