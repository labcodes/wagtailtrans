from unittest import mock

import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test import override_settings

from tests.factories.language import LanguageFactory
from tests.factories.sites import SiteFactory, SiteLanguagesFactory
from wagtailtrans.middleware import TranslationMiddleware
from wagtailtrans.models import Language


@pytest.mark.django_db
class TestTranslationMiddleware:

    def test_request_from_path(self, rf):
        get_response = mock.MagicMock()
        request = rf.get('/nl/random/page/')
        TranslationMiddleware(get_response)._process_request(request)

        assert request.LANGUAGE_CODE == 'nl'

    def test_request_default_language(self, rf):
        get_response = mock.MagicMock()
        LanguageFactory(code='en', is_default=True, live=True)
        LanguageFactory(code='fr', is_default=False, live=True)

        request = rf.get('/home/')
        TranslationMiddleware(get_response)._process_request(request)
        assert request.LANGUAGE_CODE == 'en'

    def test_request_site_language(self, rf):
        SiteLanguagesFactory(default_language__code='fr')
        get_response = mock.MagicMock()
        request = rf.get('/random/page/')

        # Backwards-compatible lookup for the deprecation of Wagtails SiteMiddleware per 2.9
        if 'wagtail.core.middleware.SiteMiddleware' in settings.MIDDLEWARE:
            request.site = SiteFactory()
        with override_settings(WAGTAILTRANS_LANGUAGES_PER_SITE=True):
            TranslationMiddleware(get_response)._process_request(request)

        assert request.LANGUAGE_CODE == 'fr'

    def test_settings_fallback(self, rf):
        get_response = mock.MagicMock()
        Language.objects.all().delete()

        request = rf.get('/random/page/')
        with override_settings(LANGUAGE_CODE='en-us'):
            TranslationMiddleware(get_response)._process_request(request)

        assert request.LANGUAGE_CODE == 'en-us'

    def test_request_language_from_header(self, rf):
        get_response = mock.MagicMock()
        Language.objects.all().delete()
        LanguageFactory(code='en', is_default=True, live=True)
        LanguageFactory(code='fr', is_default=False, live=True)

        request = rf.get('/', HTTP_ACCEPT_LANGUAGE='fr')
        TranslationMiddleware(get_response)._process_request(request)

        assert request.LANGUAGE_CODE == 'fr'

    def test_request_language_from_header_complete_match(self, rf):
        get_response = mock.MagicMock()
        Language.objects.all().delete()
        LanguageFactory(code='en-GB', is_default=True, live=True)
        LanguageFactory(code='en-US', is_default=False, live=True)

        request = rf.get('/', HTTP_ACCEPT_LANGUAGE='en-US')
        TranslationMiddleware(get_response)._process_request(request)

        assert request.LANGUAGE_CODE == 'en-US'

    def test_request_language_from_header_partial_match(self, rf):
        get_response = mock.MagicMock()
        Language.objects.all().delete()
        LanguageFactory(code='nl', is_default=True, live=True)
        LanguageFactory(code='en', is_default=False, live=True)

        request = rf.get('/', HTTP_ACCEPT_LANGUAGE='en-GB')
        TranslationMiddleware(get_response)._process_request(request)

        assert request.LANGUAGE_CODE == 'en'

    def test_request_language_from_header_multiple_first_unavailable(self, rf):
        get_response = mock.MagicMock()
        Language.objects.all().delete()
        LanguageFactory(code='fr', is_default=True, live=True)
        LanguageFactory(code='es', is_default=False, live=True)
        languages = 'nl,en-GB;q=0.8,en;q=0.6,es-419;q=0.4,es;q=0.2'

        request = rf.get('/', HTTP_ACCEPT_LANGUAGE=languages)
        TranslationMiddleware(get_response)._process_request(request)

        assert request.LANGUAGE_CODE == 'es'

    def test_request_no_languages(self, rf):
        get_response = mock.MagicMock()
        Language.objects.all().delete()
        request = rf.get('/')

        with override_settings(LANGUAGE_CODE='en'):
            TranslationMiddleware(get_response)._process_request(request)

        assert request.LANGUAGE_CODE == 'en'

    def test_response(self, rf):
        get_response = mock.MagicMock()
        request = rf.get('/nl/random/page/')
        TranslationMiddleware(get_response)._process_request(request)
        response = TranslationMiddleware(get_response)._process_response(request, HttpResponse())
        assert response['Content-Language'] == 'nl'

    def test_set_cookie_in_response(self, rf):
        get_response = mock.MagicMock()
        request = rf.get('/nl/random/page/')
        TranslationMiddleware(get_response)._process_request(request)
        response = TranslationMiddleware(get_response)._process_response(request, HttpResponse())
        assert response.cookies.get(settings.LANGUAGE_COOKIE_NAME).value == 'nl'

    def test_prefer_cookie_over_default_and_accept_header_in_request(self, rf):
        get_response = mock.MagicMock()
        Language.objects.all().delete()
        LanguageFactory(code='en', is_default=True, live=True)
        LanguageFactory(code='fr', is_default=False, live=True)
        LanguageFactory(code='nl', is_default=False, live=True)

        request = rf.get('/', HTTP_ACCEPT_LANGUAGE='fr')
        request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = 'nl'
        TranslationMiddleware(get_response)._process_request(request)
        assert request.LANGUAGE_CODE == 'nl'

    def test_prefer_path_over_cookie_in_request(self, rf):
        get_response = mock.MagicMock()
        Language.objects.all().delete()
        LanguageFactory(code='en', is_default=True, live=True)
        LanguageFactory(code='fr', is_default=False, live=True)
        LanguageFactory(code='nl', is_default=False, live=True)
        LanguageFactory(code='es', is_default=False, live=True)

        request = rf.get('/es/', HTTP_ACCEPT_LANGUAGE='fr')
        request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = 'nl'
        TranslationMiddleware(get_response)._process_request(request)
        assert request.LANGUAGE_CODE == 'es'
