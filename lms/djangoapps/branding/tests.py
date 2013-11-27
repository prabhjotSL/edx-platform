"""
Tests for branding page
"""
import datetime
from pytz import UTC
from django.conf import settings
from django.test.utils import override_settings
from django.test.client import RequestFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.django import editable_modulestore
from xmodule.modulestore.tests.factories import CourseFactory
from courseware.tests.tests import TEST_DATA_MONGO_MODULESTORE
import student.views

FEATURES_WITH_STARTDATE = settings.FEATURES.copy()
FEATURES_WITH_STARTDATE['DISABLE_START_DATES'] = False
FEATURES_WO_STARTDATE = settings.FEATURES.copy()
FEATURES_WO_STARTDATE['DISABLE_START_DATES'] = True


@override_settings(MODULESTORE=TEST_DATA_MONGO_MODULESTORE)
class AnonymousIndexPageTest(ModuleStoreTestCase):
    """
    Tests that anonymous users can access the '/' page,  Need courses with start date
    """
    def setUp(self):
        self.store = editable_modulestore()
        self.factory = RequestFactory()
        self.course = CourseFactory.create()
        self.course.days_early_for_beta = 5
        self.course.enrollment_start = datetime.datetime.now(UTC) + datetime.timedelta(days=3)
        self.store.save_xmodule(self.course)

    @override_settings(FEATURES=FEATURES_WITH_STARTDATE)
    def test_none_user_index_access_with_startdate_fails(self):
        """
        This was a "before" test for a bugfix.  If someone fixes the bug another way in the future
        and this test begins failing (but the other two pass), then feel free to delete this test.
        """
        with self.assertRaisesRegexp(AttributeError, "'NoneType' object has no attribute 'is_authenticated'"):
            student.views.index(self.factory.get('/'), user=None)  # pylint: disable=E1101

    @override_settings(FEATURES=FEATURES_WITH_STARTDATE)
    def test_anon_user_with_startdate_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    @override_settings(FEATURES=FEATURES_WO_STARTDATE)
    def test_anon_user_no_startdate_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
