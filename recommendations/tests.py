from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient
from requests.exceptions import HTTPError

from recommendations.services.search_tracks import SearchTrackService


class PublicApiTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.valid_payload = {
            'track_ids': ['A' * 22],
            'genres': ['pop'],
            'mood': 'happy',
            'start_year': 2000,
            'end_year': 2020,
        }

    def test_home_page_uses_same_origin_assets_and_form(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form id="playlistForm"')
        self.assertContains(response, 'action="/"')
        self.assertRegex(response.content.decode(), r'/static/styles(?:\.[a-f0-9]+)?\.css')
        self.assertRegex(response.content.decode(), r'/static/music_form(?:\.[a-f0-9]+)?\.js')
        self.assertNotContains(response, '127.0.0.1')

    @patch('recommendations.views.PlaylistRecommendationService.get_recommended_playlist', return_value=[])
    def test_frontend_form_fields_are_accepted(self, recommend):
        response = self.client.post('/', {
            'track_ids': ['A' * 22],
            'genres': ['pop', 'rock'],
            'mood': 'happy',
            'start_year': '2000',
            'end_year': '2020',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(recommend.call_args.kwargs['track_ids'], ['A' * 22])

    @patch('recommendations.views.PlaylistRecommendationService.get_recommended_playlist', return_value=[])
    def test_recommendations_return_documented_array(self, recommend):
        response = self.client.post('/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        recommend.assert_called_once()

    def test_recommendations_reject_bad_inputs(self):
        invalid = [
            {'mood': 'angry'},
            {'start_year': 2021, 'end_year': 2020},
            {'track_ids': ['A' * 22] * 3},
            {'track_ids': ['A' * 22, 'A' * 22]},
            {'genres': ['pop'] * 11},
        ]
        for fields in invalid:
            with self.subTest(fields=fields):
                response = self.client.post('/', self.valid_payload | fields, format='json')
                self.assertEqual(response.status_code, 400)

    @patch('recommendations.views.SearchTrackService.search_track', return_value=[])
    def test_search_requires_query_and_returns_array(self, search):
        self.assertEqual(self.client.get('/search/').status_code, 400)
        self.assertEqual(self.client.get('/search/', {'query': ' '}).status_code, 400)
        response = self.client.get('/search/', {'query': 'Hello'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        search.assert_called_once_with(search_input='Hello')

    @patch('recommendations.views.SearchTrackService.search_track', return_value=[])
    def test_search_is_throttled(self, search):
        responses = [self.client.get('/search/', {'query': 'Hello'}) for _ in range(31)]
        self.assertTrue(all(response.status_code == 200 for response in responses[:30]))
        self.assertEqual(responses[-1].status_code, 429)
        self.assertEqual(search.call_count, 30)

    @patch('recommendations.views.SearchTrackService.search_track', side_effect=RuntimeError('upstream'))
    def test_search_failure_is_safe(self, search):
        with self.assertLogs('recommendations.views', level='ERROR'):
            response = self.client.get('/search/', {'query': 'Hello'})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('upstream', str(response.json()))

    @patch('recommendations.views.PlaylistRecommendationService.get_recommended_playlist', return_value=[])
    def test_recommendations_are_throttled(self, recommend):
        responses = [self.client.post('/', self.valid_payload, format='json') for _ in range(11)]
        self.assertTrue(all(response.status_code == 200 for response in responses[:10]))
        self.assertEqual(responses[-1].status_code, 429)
        self.assertEqual(recommend.call_count, 10)

    @patch('recommendations.services.search_tracks.requests.get')
    def test_spotify_search_checks_status_and_uses_timeout(self, get):
        get.return_value.raise_for_status.side_effect = HTTPError('rate limited')
        with self.assertRaises(HTTPError):
            SearchTrackService.make_spotify_api_call('Hello', 'token')
        self.assertEqual(get.call_args.kwargs['timeout'], 5)
