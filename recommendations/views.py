import json
import logging

from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from recommendations.serializers import GetRecommendationsInputSerializer, SearchInputSerializer
from .services.playlist_recommendations import PlaylistRecommendationService
from .services.search_tracks import SearchTrackService


logger = logging.getLogger(__name__)


class Recommendations(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'recommendations'

    def get_throttles(self):
        return [] if self.request.method == 'GET' else super().get_throttles()

    def get(self, request):
        return render(request, 'recommendations/music_form.html')

    def post(self, request):
        serializer = GetRecommendationsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        input_data = serializer.validated_data

        result = PlaylistRecommendationService().get_recommended_playlist(
            track_ids=input_data['track_ids'],
            user_preferences=json.dumps({
                'genres': input_data['genres'],
                'mood': input_data['mood'],
                'start_year': input_data['start_year'],
                'end_year': input_data['end_year'],
            }),
        )
        return Response(result, status=status.HTTP_200_OK)


class SearchTracks(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'search'

    def get(self, request):
        serializer = SearchInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        try:
            tracks = SearchTrackService().search_track(search_input=serializer.validated_data['query'])
            return Response(tracks, status=status.HTTP_200_OK)
        except Exception:
            logger.exception('Spotify search failed')
            return Response({'detail': 'Search is temporarily unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
