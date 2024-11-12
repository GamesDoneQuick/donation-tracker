from tests.util import APITestCase
from tracker import models
from tracker.api.serializers import CountryRegionSerializer, CountrySerializer


class TestCountry(APITestCase):
    serializer_class = CountrySerializer
    model_name = 'country'
    lookup_key = 'numeric_or_alpha'
    id_field = 'alpha2'

    def test_fetch(self):
        with self.saveSnapshot():
            country = models.Country.objects.first()
            data = self.get_list()
            self.assertEqual(
                data['count'],
                models.Country.objects.count(),
                msg='Country count did not match',
            )
            self.assertV2ModelPresent(country, data['results'])

            with self.subTest('via numeric code'):
                data = self.get_detail(
                    country, kwargs={'numeric_or_alpha': country.numeric}
                )
                self.assertV2ModelPresent(country, data)

            with self.subTest('via alpha2'):
                data = self.get_detail(
                    country, kwargs={'numeric_or_alpha': country.alpha2}
                )
                self.assertV2ModelPresent(country, data)

            with self.subTest('via alpha3'):
                data = self.get_detail(
                    country, kwargs={'numeric_or_alpha': country.alpha3}
                )
                self.assertV2ModelPresent(country, data)

        with self.subTest('error cases'):
            self.get_detail(None, kwargs={'numeric_or_alpha': '00'}, status_code=404)
            self.get_detail(None, kwargs={'numeric_or_alpha': '000'}, status_code=404)
            self.get_detail(None, kwargs={'numeric_or_alpha': 'XX'}, status_code=404)
            self.get_detail(None, kwargs={'numeric_or_alpha': 'XXX'}, status_code=404)
            self.get_detail(
                None, kwargs={'numeric_or_alpha': 'foobar'}, status_code=404
            )


class TestCountryRegions(APITestCase):
    serializer_class = CountryRegionSerializer
    model_name = 'countryregion'

    def test_fetch(self):
        region = models.CountryRegion.objects.create(
            name='Test Region', country=models.Country.objects.first()
        )

        with self.saveSnapshot():
            data = self.get_list(model_name='region')
            self.assertEqual(
                data['count'],
                models.CountryRegion.objects.count(),
                msg='Region count did not match',
            )
            self.assertV2ModelPresent(region, data['results'])

            data = self.get_detail(region, model_name='region')
            self.assertV2ModelPresent(region, data)

            with self.subTest('via country'):
                data = self.get_noun(
                    'regions',
                    region.country,
                    lookup_key='numeric_or_alpha',
                    model_name='country',
                    kwargs={'numeric_or_alpha': region.country.alpha3},
                )
                self.assertV2ModelPresent(region, data['results'])
