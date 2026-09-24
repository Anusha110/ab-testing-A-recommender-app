import os, sys
import django

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommender.settings")
django.setup()

from recommendations.models import *
import sqlite3



# Connect the local music brainz db
connection = sqlite3.connect("../music_brainz_db")
cursor = connection.cursor()


# Get all MusicBrainz Artist IDs
music_brainz_artist_ids = list(MusicBrainzArtist.objects.values_list("id", flat=True))

artist_id_placeholders = ", ".join("?" for x in music_brainz_artist_ids)


# Fetch the artist tags from MusicBrainz
cursor.execute(f"SELECT artist_tag.tag_id as tag_id, artist_tag.artist_id as artist_id, tag.name as tag_name, artist_tag.count as tag_count FROM artist_tag INNER JOIN tag ON artist_tag.tag_id = tag.id WHERE artist_tag.artist_id IN ({artist_id_placeholders})", (music_brainz_artist_ids))
fetched_data = cursor.fetchall()

tag_records = []

# Create the MusicBrainzArtistTag records
for fetched_artist_tag in fetched_data:

    tag_records.append(
            MusicBrainzArtistTag(id=fetched_artist_tag[0],
                                    artist_id=fetched_artist_tag[1],
                                tag_name=fetched_artist_tag[2],
                                tag_count=fetched_artist_tag[3],
                                
            )
        )

# Bulk create the artist tags
created_artist_tags = MusicBrainzArtistTag.objects.bulk_create(tag_records, batch_size=2000, update_conflicts=True, unique_fields=["id"], update_fields=["artist_id", "tag_name", "tag_count"])

print("created_artist_tags count: ", len(created_artist_tags))

