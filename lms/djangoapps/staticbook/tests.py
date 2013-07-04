"""
Test the lms/staticbook views.
"""

import textwrap

import mock
import requests

from django.test.utils import override_settings
from django.core.urlresolvers import reverse, NoReverseMatch

from courseware.tests.tests import TEST_DATA_MONGO_MODULESTORE
from student.tests.factories import UserFactory, CourseEnrollmentFactory
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase


IMAGE_BOOK = ("An Image Textbook", "http://example.com/the_book/")

PDF_BOOK = {
    "tab_title": "Textbook",
    "title": "A PDF Textbook",
    "chapters": [
        { "title": "Chapter 1 for PDF", "url": "https://somehost.com/the_book/chap1.pdf" },
        { "title": "Chapter 2 for PDF", "url": "https://somehost.com/the_book/chap2.pdf" },
    ],
}

HTML_BOOK = {
    "tab_title": "Textbook",
    "title": "An HTML Textbook",
    "chapters": [
        { "title": "Chapter 1 for HTML", "url": "https://somehost.com/the_book/chap1.html" },
        { "title": "Chapter 2 for HTML", "url": "https://somehost.com/the_book/chap2.html" },
    ],
}

@override_settings(MODULESTORE=TEST_DATA_MONGO_MODULESTORE)
class StaticBookTest(ModuleStoreTestCase):
    """
    Helpers for the static book tests.
    """

    def __init__(self, *args, **kwargs):
        super(StaticBookTest, self).__init__(*args, **kwargs)
        self.course = None

    def make_course(self, **kwargs):
        """
        Make a course with an enrolled logged-in student.
        """
        self.course = CourseFactory.create(**kwargs)
        user = UserFactory.create()
        CourseEnrollmentFactory.create(user=user, course_id=self.course.id)
        self.client.login(username=user.username, password='test')

    def make_url(self, url_name, **kwargs):
        """
        Make a URL for a `url_name` using keyword args for url slots.

        Automatically provides the course id.

        """
        kwargs['course_id'] = self.course.id
        url = reverse(url_name, kwargs=kwargs)
        return url


class StaticImageBookTest(StaticBookTest):
    """
    Test the image-based static book view.
    """

    def test_book(self):
        # We can access a book.
        with mock.patch.object(requests, 'get') as mock_get:
            mock_get.return_value.text = textwrap.dedent('''\
                <?xml version="1.0"?>
                <table_of_contents>
                <entry page="9" page_label="ix" name="Contents!?"/>
                <entry page="1" page_label="i" name="Preamble">
                    <entry page="4" page_label="iv" name="About the Elephants"/>
                </entry>
                </table_of_contents>
                ''')

            self.make_course(textbooks=[IMAGE_BOOK])
            url = self.make_url('book', book_index=0)
            response = self.client.get(url)

        self.assertContains(response, "Contents!?")
        self.assertContains(response, "About the Elephants")

    def test_bad_book_id(self):
        # A bad book id will be a 404.
        self.make_course(textbooks=[IMAGE_BOOK])
        with self.assertRaises(NoReverseMatch):
            self.make_url('book', book_index='fooey')

    def test_out_of_range_book_id(self):
        self.make_course()
        url = self.make_url('book', book_index=0)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class StaticPdfBookTest(StaticBookTest):
    """
    Test the PDF static book view.
    """

    def test_book(self):
        # We can access a book.
        self.make_course(pdf_textbooks=[PDF_BOOK])
        url = self.make_url('pdf_book', book_index=0)
        response = self.client.get(url)
        self.assertContains(response, "Chapter 1 for PDF")
        self.assertNotContains(response, "options.chapterNum =")
        self.assertNotContains(response, "options.pageNum =")

    def test_book_chapter(self):
        # We can access a book at a particular chapter.
        self.make_course(pdf_textbooks=[PDF_BOOK])
        url = self.make_url('pdf_book', book_index=0, chapter=2)
        response = self.client.get(url)
        self.assertContains(response, "Chapter 2 for PDF")
        self.assertContains(response, "options.chapterNum = 2;")
        self.assertNotContains(response, "options.pageNum =")

    def test_book_page(self):
        # We can access a book at a particular page.
        self.make_course(pdf_textbooks=[PDF_BOOK])
        url = self.make_url('pdf_book', book_index=0, page=17)
        response = self.client.get(url)
        self.assertContains(response, "Chapter 1 for PDF")
        self.assertNotContains(response, "options.chapterNum =")
        self.assertContains(response, "options.pageNum = 17;")

    def test_book_chapter_page(self):
        # We can access a book at a particular chapter and page.
        self.make_course(pdf_textbooks=[PDF_BOOK])
        url = self.make_url('pdf_book', book_index=0, chapter=2, page=17)
        response = self.client.get(url)
        self.assertContains(response, "Chapter 2 for PDF")
        self.assertContains(response, "options.chapterNum = 2;")
        self.assertContains(response, "options.pageNum = 17;")

    def test_bad_book_id(self):
        # If the book id isn't an int, we'll get a 404.
        self.make_course(pdf_textbooks=[PDF_BOOK])
        with self.assertRaises(NoReverseMatch):
            self.make_url('pdf_book', book_index='fooey', chapter=1)

    def test_out_of_range_book_id(self):
        # If we have one book, asking for the second book will fail with a 404.
        self.make_course(pdf_textbooks=[PDF_BOOK])
        url = self.make_url('pdf_book', book_index=1, chapter=1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_no_book(self):
        # If we have no books, asking for the first book will fail with a 404.
        self.make_course()
        url = self.make_url('pdf_book', book_index=0, chapter=1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_chapter_xss(self):
        # The chapter in the URL used to go right on the page.
        self.make_course(pdf_textbooks=[PDF_BOOK])
        # It's no longer possible to use a non-integer chapter.
        with self.assertRaises(NoReverseMatch):
            self.make_url('pdf_book', book_index=0, chapter='xyzzy')

    def test_page_xss(self):
        # The page in the URL used to go right on the page.
        self.make_course(pdf_textbooks=[PDF_BOOK])
        # It's no longer possible to use a non-integer page.
        with self.assertRaises(NoReverseMatch):
            self.make_url('pdf_book', book_index=0, page='xyzzy')

    def test_chapter_page_xss(self):
        # The page in the URL used to go right on the page.
        self.make_course(pdf_textbooks=[PDF_BOOK])
        # It's no longer possible to use a non-integer page and a non-integer chapter.
        with self.assertRaises(NoReverseMatch):
            self.make_url('pdf_book', book_index=0, chapter='fooey', page='xyzzy')


class StaticHtmlBookTest(StaticBookTest):
    """
    Test the HTML static book view.
    """

    def test_book(self):
        # We can access a book.
        self.make_course(html_textbooks=[HTML_BOOK])
        url = self.make_url('html_book', book_index=0)
        response = self.client.get(url)
        self.assertContains(response, "Chapter 1 for HTML")
        self.assertNotContains(response, "options.chapterNum =")

    def test_book_chapter(self):
        # We can access a book at a particular chapter.
        self.make_course(html_textbooks=[HTML_BOOK])
        url = self.make_url('html_book', book_index=0, chapter=2)
        response = self.client.get(url)
        self.assertContains(response, "Chapter 2 for HTML")
        self.assertContains(response, "options.chapterNum = 2;")

    def test_bad_book_id(self):
        # If we have one book, asking for the second book will fail with a 404.
        self.make_course(html_textbooks=[HTML_BOOK])
        url = self.make_url('html_book', book_index=1, chapter=1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_no_book(self):
        # If we have no books, asking for the first book will fail with a 404.
        self.make_course()
        url = self.make_url('html_book', book_index=0, chapter=1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_chapter_xss(self):
        # The chapter in the URL used to go right on the page.
        self.make_course(pdf_textbooks=[HTML_BOOK])
        # It's no longer possible to use a non-integer chapter.
        with self.assertRaises(NoReverseMatch):
            self.make_url('html_book', book_index=0, chapter='xyzzy')