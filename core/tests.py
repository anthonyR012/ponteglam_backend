from rest_framework.test import APITestCase
from rest_framework import status
from core.models import Type, Category, MobileAppLog
from users.models import User
from cities_light.models import City, Country
from django.urls import reverse


class TypeListViewTest(APITestCase):
    def setUp(self):
        # Crea algunos objetos de tipo Type en la base de datos
        self.category_type = Category.objects.create(code='Category Type 1',
                                                     created_by_user_id=1)
        self.type1 = Type.objects.create(code='Type 1',
                                         category_type=self.category_type,
                                         created_by_user_id=1)
        self.type2 = Type.objects.create(code='Type 2',
                                         category_type=self.category_type,
                                         created_by_user_id=1)
        self.type3 = Type.objects.create(code='Type 3',
                                         category_type=self.category_type,
                                         created_by_user_id=1)

    def test_list_types(self):
        # Realiza una solicitud GET a la vista que lista los tipos
        url = reverse('list-types-list')
        response = self.client.get(url)
        # import pdb; pdb.set_trace()

        # Verifica que la solicitud se haya realizado correctamente
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verifica que se devuelvan los tipos correctos en la respuesta
        self.assertEqual(len(response.data['success']), 3)
        self.assertEqual(response.data['success'][0]['code'], self.type1.code)
        self.assertEqual(response.data['success'][1]['code'], self.type2.code)
        self.assertEqual(response.data['success'][2]['code'], self.type3.code)

    def test_list_types_empty(self):
        # Elimina todos los tipos de la base de datos
        Type.objects.all().delete()

        # Realiza una solicitud GET a la vista
        url = reverse('list-types-list')
        response = self.client.get(url)

        # Verifica que la respuesta esté vacía
        self.assertEqual(response.data['success'], [])


class CountryListViewTest(APITestCase):
    def setUp(self):
        # Crea algunos objetos de tipo Country en la base de datos
        self.country1 = Country.objects.create(name='Country 1',
                                               slug='country-1')
        self.country2 = Country.objects.create(name='Country 2',
                                               slug='country-1')
        self.country3 = Country.objects.create(name='Country 3',
                                               slug='country-1')

    def test_list_countries(self):
        # Realiza una solicitud GET a la vista que lista los paises
        url = reverse('list-countries-list')
        response = self.client.get(url)

        # Verifica que la solicitud se haya realizado correctamente
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verifica que se devuelvan los paises correctos en la respuesta
        self.assertEqual(len(response.data['success']), 3)
        self.assertEqual(response.data['success'][0]['name'],
                         self.country1.name)
        self.assertEqual(response.data['success'][1]['name'],
                         self.country2.name)
        self.assertEqual(response.data['success'][2]['name'],
                         self.country3.name)

    def test_list_countries_empty(self):
        # Elimina todos los paises de la base de datos
        Country.objects.all().delete()

        # Realiza una solicitud GET a la vista
        url = reverse('list-countries-list')
        response = self.client.get(url)

        # Verifica que la respuesta está vacía
        self.assertEqual(response.data['success'], [])


class CityListViewTest(APITestCase):
    def setUp(self):
        # Crea algunos objetos de tipo City en la base de datos
        self.country1 = Country.objects.create(name='Country 1',
                                               slug='country-1')
        self.city1 = City.objects.create(name='City 1', display_name='City 1',
                                         slug='city-1', country=self.country1)
        self.city2 = City.objects.create(name='City 2', display_name='City 2',
                                         slug='city-1', country=self.country1)
        self.city3 = City.objects.create(name='City 3', display_name='City 3',
                                         slug='city-1', country=self.country1)

    def test_list_cities(self):
        # Realiza una solicitud GET a la vista que lista las ciudades
        url = reverse('list-cities-list')
        response = self.client.get(url)

        # Verifica que la solicitud se haya realizado correctamente
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verifica que se devuelvan las ciudades correctas en la respuesta
        self.assertEqual(len(response.data['success']), 3)
        self.assertEqual(response.data['success'][0]['name'], self.city1.name)
        self.assertEqual(response.data['success'][1]['name'], self.city2.name)
        self.assertEqual(response.data['success'][2]['name'], self.city3.name)

    def test_list_cities_empty(self):
        # Elimina todas las ciudades de la base de datos
        City.objects.all().delete()

        # Realiza una solicitud GET a la vista
        url = reverse('list-cities-list')
        response = self.client.get(url)

        # Verifica que la respuesta está vacía
        self.assertEqual(response.data['success'], [])


class CreateMobileAppLogViewTest(APITestCase):
    def setUp(self):
        # Crea un usuario de prueba
        self.user = User.objects.create(username='testuser',
                                        password='testpassword')

    def test_create_mobile_app_log(self):
        # Autentica al usuario
        self.client.force_authenticate(user=self.user)

        # Datos para crear el log de la aplicación móvil
        data = [
            {
                'device_info': 'Device 1',
                'description': 'Log 1',
                'source': 'Source 1'
            },
            {
                'device_info': 'Device 2',
                'description': 'Log 2',
                'source': 'Source 2'
            },
            {
                'device_info': 'Device 3',
                'description': 'Log 3',
                'source': 'Source 3'
            }
        ]

        # Realiza una solicitud POST a la vista para crear los logs
        url = '/core/api/create-mobile-app-log/'
        response = self.client.post(url, data, format='json')

        # Verifica que la solicitud se haya realizado correctamente
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verifica que los logs se hayan creado correctamente en la bd
        self.assertEqual(MobileAppLog.objects.count(), 3)

        # Verifica que el usuario creador sea el usuario autenticado
        for log in MobileAppLog.objects.all():
            self.assertEqual(log.created_by_user_id, self.user.pk)
