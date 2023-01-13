from django.conf import settings
from django.utils import translation
from django.utils.translation import get_language_from_path
from django.utils.translation.trans_real import get_supported_language_variant

from wagtail.core.models import Site

from .models import Language
from .sites import get_languages_for_site


def get_language_from_request(request):
    """
    Analyze the request to find what language the user wants the system to
    show. Only languages listed in settings.LANGUAGES are taken into account.
    If the user requests a sublanguage where we have a main language, we send
    out the main language.

    The URL path prefix will be checked for a language code.
    """
    lang_code = get_language_from_path(request.path_info)
    if lang_code is not None:
        return lang_code

    lang_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)

    try:
        return get_supported_language_variant(lang_code)
    except LookupError:
        return None


class TranslationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _request = self._process_request(request)
        _response = self.get_response(_request)
        response = self._process_response(
            request=request,
            response=_response
        )
        return response


    def _process_request(self, request):
        active_language = None

        language_from_request = get_language_from_request(request)
        requested_languages = request.headers.get('accept-language')

        # Backwards-compatible lookup for the deprecation of Wagtails SiteMiddleware per 2.9
        if 'wagtail.core.middleware.SiteMiddleware' in settings.MIDDLEWARE:
            site = request.site
        else:
            site = Site.find_for_request(request)

        if language_from_request:
            active_language = language_from_request
        elif requested_languages:
            requested_languages = requested_languages.split(',')
            codes = tuple(language.code for language in get_languages_for_site(site) if language)

            for language in requested_languages:
                language = language.split(';')[0]
                active_language = language if language in codes else None

                if active_language is None and language.startswith(codes):
                    active_language = [c for c in codes if language.startswith(c)][0]
                if active_language is not None:
                    break

        if active_language is None:
            default_language = Language.objects.default_for_site(site=site)

            if default_language:
                active_language = default_language.code
            else:
                active_language = settings.LANGUAGE_CODE

        translation.activate(active_language)
        request.LANGUAGE_CODE = active_language
        return request

    def _process_response(self, request, response):
        if 'Content-Language' not in response:
            response['Content-Language'] = request.LANGUAGE_CODE

        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME, request.LANGUAGE_CODE,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
        )
        return response
