from datetime import date

from rest_framework import serializers


class GetRecommendationsInputSerializer(serializers.Serializer):
    track_ids = serializers.ListField(
        child=serializers.RegexField(regex=r'^[A-Za-z0-9]{22}$'),
        required=False,
        allow_empty=True,
        max_length=2,
        default=list,
    )
    genres = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True,
        max_length=10,
        default=list,
    )
    mood = serializers.ChoiceField(choices=['happy', 'neutral', 'sad'])
    start_year = serializers.IntegerField(min_value=1900, max_value=date.today().year)
    end_year = serializers.IntegerField(min_value=1900, max_value=date.today().year)

    def validate(self, data):
        if data['start_year'] > data['end_year']:
            raise serializers.ValidationError({'end_year': 'Must be greater than or equal to start_year.'})
        if len(data['track_ids']) != len(set(data['track_ids'])):
            raise serializers.ValidationError({'track_ids': 'Seed tracks must be unique.'})
        return data


class SearchInputSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=100, trim_whitespace=True)
