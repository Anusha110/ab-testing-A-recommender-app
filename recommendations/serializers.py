from recommendations.models import SpotifyTrack
from rest_framework import serializers


class GetRecommendationsInputSerializer(serializers.Serializer):

    track_ids = serializers.ListField(
          child=serializers.CharField(max_length=255),
          required=False,
          allow_empty=True,
          default=list
      )
    
    genres = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        allow_empty=True,
        default=list
    )

    mood = serializers.CharField(max_length=30, required=True)
    start_year = serializers.IntegerField(required=True)
    end_year = serializers.IntegerField(required=True)

    def validate(self, data):
        if not data.get("mood"):
            raise serializers.ValidationError("Mood is required")
        if not data.get("start_year"):
            raise serializers.ValidationError("Start year is required")
        if not data.get("end_year"):
            raise serializers.ValidationError("End year is required")
        return data