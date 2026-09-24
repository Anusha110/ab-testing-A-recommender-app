from rest_framework.views import APIView
import json
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from recommendations.serializers import GetRecommendationsInputSerializer
from .services.playlist_recommendations import PlaylistRecommendationService
from .services.search_tracks import SearchTrackService


# This API gets the playlist recommendations for the given track ids and user preferences.
class Recommendations(APIView):

    def post(self, request):

        serializer = GetRecommendationsInputSerializer(data=request.data)

        if serializer.is_valid():

            input_data = serializer.validated_data

            service = PlaylistRecommendationService()

            result = service.get_recommended_playlist(
                track_ids=input_data["track_ids"],
                user_preferences=json.dumps({
                    "genres": input_data["genres"],
                    "mood": input_data["mood"],
                    "start_year": input_data["start_year"],
                    "end_year": input_data["end_year"],
                }),
            )

            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# This API searches for the given query in Spotify and returns the search results.
class SearchTracks(APIView):

    def get(self, request):

        search_input = request.query_params.get("query")

        try: 
            service = SearchTrackService()
            response_tracks = service.search_track(search_input=search_input)

            return Response(response_tracks, status=status.HTTP_200_OK)
        
        except Exception as e:

            return Response("Error Searching For Tracks", status=status.HTTP_500_INTERNAL_SERVER_ERROR)



