from django.contrib import admin
from .models import SpotifyTrack, SpotifyTrackEmbedding, MusicBrainzArtist, MusicBrainzArtistTag
# Register your models here.


admin.site.register(SpotifyTrack)
admin.site.register(MusicBrainzArtist)
admin.site.register(MusicBrainzArtistTag)