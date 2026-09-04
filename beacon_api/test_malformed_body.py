"""A malformed JSON body must answer 400, not 500.

The bug under test
------------------
``views_boolean`` reads the POST body via DRF's ``request.data``. When the body
is not valid JSON, DRF raises ``rest_framework.exceptions.ParseError`` — a
400-class exception it would normally render itself. But that access sits
inside a ``try`` whose final ``except Exception`` returns 500, so the caller was
told the server had failed when in fact their request was malformed.

Found from the developer tutorial: step 9b shipped a literal ``<POS>``
placeholder in the POST body, and a reader who pasted it got

    {"error": {"errorCode": 500, "errorMessage": "An error occurred ..."}}

A 500 tells a client author to look at the server. A 400 tells them to look at
their request, which is where the fault actually was.

Needs Django and the project settings, so it runs in the container or
wherever the app itself runs — unlike the Django-free suites.

    python3 -m unittest beacon_api.test_malformed_body -v
"""
import os
import unittest

# Use the project's own settings rather than a hand-rolled subset: the view
# reads a dozen BEACON_* values, and guessing which ones only moves the failure
# around.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beacon_project.settings_boolean')

import django  # noqa: E402

django.setup()

from rest_framework import status  # noqa: E402
from rest_framework.exceptions import ParseError  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from beacon_api import views_boolean  # noqa: E402


class TestMalformedJsonBody(unittest.TestCase):

    def post(self, body):
        request = APIRequestFactory().post(
            '/api/g_variants', data=body, content_type='application/json')
        return views_boolean.variant_query_boolean(request)

    def test_a_body_that_is_not_json_is_the_callers_fault(self):
        # The tutorial's placeholder, verbatim: <POS> is not a JSON value.
        response = self.post(
            '{"query":{"requestParameters":{"assemblyId":"GRCh38",'
            '"referenceName":"1","start":<POS>}}}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_error_says_the_body_could_not_be_parsed(self):
        # A 400 whose message does not mention the body sends the reader
        # hunting through their parameters instead of their quoting.
        response = self.post('{"query": not json}')
        message = response.data['error']['errorMessage'].lower()
        self.assertTrue(
            any(w in message for w in ('json', 'parse', 'body', 'malformed')),
            f"unhelpful message: {response.data['error']['errorMessage']!r}")

    def test_the_envelope_is_still_well_formed(self):
        # A client parsing errors must not need a second code path for this one.
        response = self.post('}{')
        self.assertIn('meta', response.data)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error']['errorCode'],
                         status.HTTP_400_BAD_REQUEST)

    def test_parse_error_is_not_reported_as_a_server_fault(self):
        # Guards the specific regression: the broad `except Exception` at the
        # end of the view must not be what handles ParseError.
        response = self.post('nonsense')
        self.assertNotEqual(response.status_code,
                            status.HTTP_500_INTERNAL_SERVER_ERROR)


if __name__ == '__main__':
    unittest.main()
