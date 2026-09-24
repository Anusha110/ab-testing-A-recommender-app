import os, sys
import django

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommender.settings")
django.setup()

from recommendations.models import *
import sqlite3
from collections import defaultdict


# Connect the local music brainz db
connection = sqlite3.connect("../music_brainz_db")
cursor = connection.cursor()

BULK_SIZE = 4000

# Get all Spotify Track IDs and Artist Names
#   - Iterate over the Spotify Tracks in bulks of 4000 tracks. (.iterator(chunk_size=000))
spotify_tracks = SpotifyTrack.objects.values_list("track_id", "artist_name").iterator(chunk_size=BULK_SIZE)


bulk_count = 0

import time

artist_name_wise_track_ids = defaultdict(list)

start_time = time.time()
print("Starting Time: ", start_time)

for track_id, artist_name in spotify_tracks:

    artist_name_wise_track_ids[artist_name].append(track_id)

    bulk_count +=1

    # Perform Database queries in bulks of 4000 tracks, to avoid timeouts.
    if bulk_count%BULK_SIZE == 0 :

        ## Create Artists
        all_spotify_artist_names = list(artist_name_wise_track_ids.keys())
        placeholders = ", ".join("?" for x in all_spotify_artist_names)

        # Fetch artists from MusicBrainz
        cursor.execute(f"SELECT artist.id as artist_id, artist.name as artist_name, artist.gid as artist_gid FROM artist WHERE artist_name IN ({placeholders})", (all_spotify_artist_names))
        fetched_artists = cursor.fetchall()

        records = []


        for fetched_artist in fetched_artists:
            records.append(
                MusicBrainzArtist(id=fetched_artist[0],
                                    artist_name=fetched_artist[1],
                                    music_brainz_id=fetched_artist[2],)
            )

        
        # Bulk create artists
        created_artists = MusicBrainzArtist.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=["artist_name", "music_brainz_id"],
            batch_size=BULK_SIZE)


        # Update Spotify Data Artist Foreign Key
        music_brainz_artists = MusicBrainzArtist.objects.values_list("id", "artist_name")

        for id, artist_name in music_brainz_artists:

            track_ids = artist_name_wise_track_ids[artist_name]

            SpotifyTrack.objects.filter(track_id__in=track_ids).update(artist=id)


        # RESET VARIABLES
        artist_name_wise_track_ids = defaultdict(list)

        batch_number = bulk_count/BULK_SIZE
        
        print("Completed processing 4000 tracks, batch_no: ", batch_number)
        print("Total time taken: ", time.time() - start_time)
