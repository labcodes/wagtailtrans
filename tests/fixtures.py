import pytest
from wagtail.core.models import Page, Site

from tests._sandbox.pages.models import HomePage
from tests.factories.requests import RequestFactory
from wagtailtrans.models import Language, TranslatableSiteRootPage

LANG_CODES = ['es', 'fr', 'de', 'nl', 'en']


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # Remove some initial data that is brought by the sandbox module
        Site.objects.all().delete()
        Page.objects.all().exclude(depth=1).delete()


@pytest.fixture
def sites():
    for code in LANG_CODES:
        site_root = TranslatableSiteRootPage.add_root(title='site root %s.localhost' % code)
        site_root.save()
        language = Language.objects.get(code=code)
        page = HomePage(
            title=f'{code} title',
            subtitle=f'{code} subtitle',
            language=language,
            body=f'{code} body',
        )
        site_root.add_child(instance=page)
        Site.objects.create(
            hostname=f'{code}.localhost',
            port=8000,
            root_page=site_root,
        )
    return Site.objects.all()


@pytest.fixture
def languages():
    for i, code in enumerate(LANG_CODES, 1):
        Language.objects.get_or_create(
            code=code, defaults={
                'is_default': True,
                'position': i,
                'live': True,
            },
        )
    return Language.objects.all()
