from django.db.models import Case, ExpressionWrapper, F, FloatField, Value, When


MIN_TEMPO = 60.0
MAX_TEMPO = 200.0

class MoodScoreService:

    @staticmethod
    def calculate_mood_score(spotify_track_queryset):

        # Tempo is normalized to the same range as danceability and valence
        normalized_tempo = Case(
            When(tempo__lt=MIN_TEMPO, then=Value(0.0)),
            When(tempo__gt=MAX_TEMPO, then=Value(1.0)),
            default=ExpressionWrapper(
                (F("tempo") - Value(MIN_TEMPO)) / Value(MAX_TEMPO - MIN_TEMPO),
                output_field=FloatField(),
                ),
            output_field=FloatField(),
        )

        # Mood score is the average of danceability, valence, and temp
        mood_score = ExpressionWrapper(
            (normalized_tempo + F("danceability") + F("valence")) / Value(3.0),
            output_field=FloatField(),
            )
        return spotify_track_queryset.annotate(mood_score=mood_score)
