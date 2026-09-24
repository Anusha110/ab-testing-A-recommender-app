
from django.core.cache import cache
import requests
import os

client_id = os.environ.get('SPOTIFY_CLIENT_ID')
client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')

cache_key = f'spotify_access_token:{client_id}'

from recommendations.models import SpotifyTrack

class SearchTrackService:

    def search_track(self, search_input: str):

        # Get access token and call Spotify Web API to search.
        access_token = self.get_access_token()
        response = self.make_spotify_api_call(search_input=search_input, access_token=access_token)

        # Parse the response from Spotify
        tracks = response.get("tracks", {}).get("items", [])
        track_ids = [track["id"] for track in tracks]

        # Search for those tracks in our local spotify database
        spotify_tracks = SpotifyTrack.objects.filter(track_id__in=track_ids).values("track_id", "track_name", "artist_name", "genre")

        response_track_list = []

        # Return information about each track for display.
        for track in spotify_tracks:

            response_track_list.append(
                {
                    "track_id": track["track_id"],
                    "track_name": track["track_name"],
                    "artist_name": track["artist_name"],
                    "genre": track["genre"],
                }
            )

        return response_track_list

    @staticmethod
    def get_access_token():
        if not client_id or not client_secret:
            raise RuntimeError('Spotify credentials are not configured')

        # Try to get access token from the cache
        access_token = cache.get(cache_key)

        if access_token is None:
            # Make request to Spotify for client credentials
            response_data = requests.post(
                "https://accounts.spotify.com/api/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret},
                timeout=5)

            response_data.raise_for_status()

            response_json = response_data.json()

            # Reading the response_json
            access_token = response_json['access_token']
            expires_in = response_json['expires_in']

            # Set access token expiry with a 5 minutes buffer, so we get a new access token 5 minutes
            # before it expires
            access_token_buffer = 300
            expires_in_with_5_minute_buffer = max(1, expires_in - access_token_buffer)

            # Setting the access token in cache with expiry
            cache.set(cache_key, access_token, timeout=expires_in_with_5_minute_buffer)

            return access_token
        else:
            return access_token

    @staticmethod
    def make_spotify_api_call(search_input: str, access_token: str):

        custom_headers = {"Authorization": f"Bearer {access_token}"}

        # Make API call to Spotify Service to search for songs.
        response = requests.get(
            'https://api.spotify.com/v1/search',
            headers=custom_headers,
            params={"q": search_input, "type": "track", "market": "ES"},
            timeout=5,
        )

        response.raise_for_status()
        # Convert Response to json
        data = response.json()

        return data
