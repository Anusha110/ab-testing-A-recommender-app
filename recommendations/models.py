from django.db import models


class SpotifyTrack(models.Model):
    serial_number = models.PositiveIntegerField(blank=True, null=True)
    artist_name = models.CharField(max_length=100)
    track_name = models.CharField(max_length=600)
    track_id = models.CharField(max_length=22, primary_key=True)
    popularity = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    genre = models.CharField(max_length=50, blank=True)
    danceability = models.FloatField()
    energy = models.FloatField()
    key = models.PositiveSmallIntegerField()
    loudness = models.FloatField()
    mode = models.PositiveSmallIntegerField()
    speechiness = models.FloatField()
    acousticness = models.FloatField()
    instrumentalness = models.FloatField()
    liveness = models.FloatField()
    valence = models.FloatField()
    tempo = models.FloatField()
    duration_ms = models.PositiveIntegerField()
    time_signature = models.PositiveSmallIntegerField()
    artist = models.ForeignKey("MusicBrainzArtist", on_delete=models.SET_NULL,
                               null=True, blank=True, related_name="tracks")

    def __str__(self):
        return f"{self.track_name} by {self.artist_name}"

    class Meta:
        indexes = [
            models.Index(fields=["track_id"], name="track_id_idx"),
        ]

class MusicBrainzArtist(models.Model):
    id = models.IntegerField(primary_key=True)
    artist_name = models.CharField(max_length=255)
    music_brainz_id = models.UUIDField(unique=True)

class MusicBrainzArtistTag(models.Model):
    id = models.IntegerField(primary_key=True)
    artist = models.ForeignKey(MusicBrainzArtist, on_delete=models.CASCADE, related_name="tags")
    tag_name = models.CharField(max_length=255)
    tag_count = models.IntegerField()

    class Meta:
        indexes= [
            models.Index(fields=["id"], name="artist_tag_track_id_idx"),
        ]


class SpotifyTrackEmbedding(models.Model):
    track_id = models.CharField(max_length=22, primary_key=True)
    danceability_norm = models.FloatField()
    energy_norm = models.FloatField()
    loudness_norm = models.FloatField()
    mode_norm = models.FloatField()
    speechiness_norm = models.FloatField()
    acousticness_norm = models.FloatField()
    instrumentalness_norm = models.FloatField()
    liveness_norm = models.FloatField()
    valence_norm = models.FloatField()
    tempo_norm = models.FloatField()
    duration_ms_norm = models.FloatField()
    popularity_norm = models.FloatField()

    class Meta:
        indexes= [
            models.Index(fields=["track_id"], name="embedding_track_id_idx"),
        ]
