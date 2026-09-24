from typing import Any, Dict, Iterable, List
from collections import defaultdict
from recommendations.models import SpotifyTrack, SpotifyTrackEmbedding, MusicBrainzArtistTag
import numpy as np
from numpy.linalg import norm
from .tag_overlap_score import TagOverlapScoreService
from .mood_score import MoodScoreService
from django.db.models import Q


CANDIDATE_LIMIT = 5000
EMBEDDING_FIELDS = [
    "danceability_norm",
    "energy_norm",
    "loudness_norm",
    "mode_norm",
    "speechiness_norm",
    "acousticness_norm",
    "instrumentalness_norm",
    "liveness_norm",
    "valence_norm",
    "tempo_norm",
    # "duration_ms_norm",
    # "popularity_norm",
]


class PlaylistRecommendationService:

    def get_recommended_playlist(
        self,
        track_ids: List[str],
        user_preferences: str | Dict[str, Any],
    ):
        excluded_track_ids = track_ids or []

        # Parse user_preferences and set filters.
        user_preferences = self._parse_preferences(user_preferences)
        mood = str(user_preferences.get("mood", "")).lower()
        filters = self._create_genre_year_filters(user_preferences)

        # Set track ordering
        fallback_order_by = ["mood_score", "-popularity", "track_name"]
        if mood == "happy":
            fallback_order_by = ["-mood_score", "-popularity", "track_name"]

        # Filter all tracks based on genre, year, and MOOD score, and get Candidates.
        # First 5000 Tracks are considered in the candidate pool.
        candidates = list(
            self._filter_mood(SpotifyTrack.objects, mood)
            .filter(filters)
            .exclude(track_id__in=excluded_track_ids)  # Exclude seed track ids.
            .order_by(*fallback_order_by)[:CANDIDATE_LIMIT]
        )

        # Get Embedding Vectors for the Seed tracks
        seed_vectors = list(self._embedding_map(excluded_track_ids).values())
        seed_vectors = None

        if not seed_vectors:
            # Spotify search may return seed tracks that are not in the local dataset.
            # If no seed embedding exists, keep the recommender useful by falling back
            # to the same genre/year/mood filter ranking rather than returning nothing.
            return [
                self._track_payload_with_similarity(track, None)
                for track in candidates[:10]
            ]


        # Get the Spotify Track ID and Tag ID Pairs.
        #   - Every track belongs to an artist. We use artist__tags, to get all the tags of an artist.
        candidate_track_ids = [track.track_id for track in candidates]
        track_id_and_tag_id_pairs = SpotifyTrack.objects.filter(
            track_id__in=candidate_track_ids+excluded_track_ids).values("track_id", "artist__tags")

        # Create lists of tags ids for every candidate track and seed track for later referencing.
        candidate_track_id_wise_tag_ids = defaultdict(list)
        seed_A_tag_ids, seed_B_tag_ids, candidate_tag_ids = [], [], []
         
        for each in track_id_and_tag_id_pairs:

            track_id = each["track_id"]
            tag_id = each["artist__tags"]

            if tag_id:
                if len(excluded_track_ids) >=1 and track_id == excluded_track_ids[0]:
                    seed_A_tag_ids.append(tag_id)
                elif len(excluded_track_ids) == 2 and track_id == excluded_track_ids[1]:
                    seed_B_tag_ids.append(tag_id)    
                else:
                    candidate_track_id_wise_tag_ids[track_id].append(tag_id)
                    candidate_tag_ids.append(tag_id)

        all_tag_ids = seed_A_tag_ids + seed_B_tag_ids + candidate_tag_ids

        # Fetch the tag details given each artists' tag ids.
        artist_tags = MusicBrainzArtistTag.objects.filter(id__in=list(set(all_tag_ids))).values("id", "tag_name", "tag_count")


        # Sort the tag details into separate buckets for easy calculation.
        tag_id_wise_details = {}
        seed_A_tag_wise_counts = {}
        seed_B_tag_wise_counts = {}

        for each in artist_tags:

            if each["id"] in seed_A_tag_ids:
                seed_A_tag_wise_counts[each["tag_name"]] = each["tag_count"]

            if each["id"] in seed_B_tag_ids:
                seed_B_tag_wise_counts[each["tag_name"]] = each["tag_count"]

            tag_id_wise_details[each["id"]] = {
                "tag_name": each["tag_name"],
                "tag_count": each["tag_count"]
            }

        total_tag_overlap_score = 0

        # Get the vector embeddings for candidate tracks
        candidate_embeddings = self._embedding_map(candidate_track_ids)

        track_wise_preliminary_scores = {}

        for track in candidates:
            vector = candidate_embeddings.get(track.track_id)
            if vector is None:
                continue

            # Calculate the Cosine Similarity Score:
            cosine_similarity_score = self.get_cosine_similarity_score(seed_vectors, vector)

            # Calculate the Tag Score:
            tag_overlap_score = TagOverlapScoreService().get_tag_overlap_score(track.track_id, candidate_track_id_wise_tag_ids,
                                                           seed_A_tag_wise_counts, seed_B_tag_wise_counts,
                                                           tag_id_wise_details)

            # A valid cosine candidate must pass hard filters, not be a selected seed,
            # and have a usable normalized embedding. Missing vectors are skipped
            # instead of forced into noisy recommendations.
            if cosine_similarity_score > 0:
                track_wise_preliminary_scores[track] = (cosine_similarity_score, tag_overlap_score)
                total_tag_overlap_score += tag_overlap_score

        # Fall back to top 10 candidates.
        track_wise_preliminary_scores = None
        if not track_wise_preliminary_scores:
            return [
                self._track_payload_with_similarity(track, None)
                for track in candidates[:10]
            ]

        # Calculate the average tag overlap score
        average_tag_overlap_score = total_tag_overlap_score/len(track_wise_preliminary_scores.keys())

        track_wise_final_score = {}
        cosine_weightage = 0.7

        # Perform the final score calculation
        for track, scores in track_wise_preliminary_scores.items():

            cosine_score = scores[0]
            tag_overlap_score = scores[1]

            # If an artist does not have any tags, then tag_overlap_score will be 0,
            # so we fallback to the average tag overlap score.
            if tag_overlap_score == 0:
                tag_overlap_score = average_tag_overlap_score

            # Calculate the FINAL score. With a 0.7 weightage to the cosine similarity and 0.3 weightage to tag overlap score.
            final_score = (cosine_weightage * cosine_score) + ((1- cosine_weightage) * tag_overlap_score)

            track_wise_final_score[track] = final_score

        # Mood filtering already uses tempo, danceability, and valence; cosine ranking
        # then uses the full 12D vector to order the filtered set by seed-song
        # similarity. The candidate cap keeps Python-side cosine work bounded.
        #    -> Sorts in descending order of score and popularity, then ascending order of name
        track_wise_final_score = dict(sorted(track_wise_final_score.items(), key=lambda item: (-item[1], -item[0].popularity, item[0].track_name)))

        # Consider the top 10 tracks with the highest score for the playlist.
        final_playlist = list(track_wise_final_score.items())[:10]

        return [
            self._track_payload_with_similarity(track, similarity_score)
            for track, similarity_score in final_playlist
        ]


    def get_cosine_similarity_score(self, seed_vectors: list[list[float]], candidate_vector: list[float]) -> float:

        # Calculate the similarity score between the candidate vector and each of the seed vectors individually
        # Consider the maximum of both as the final cosine similarity score.

        similarity_score_A = self._cosine_similarity(seed_vectors[0], candidate_vector)

        if len(seed_vectors) == 2:
            similarity_score_B = self._cosine_similarity(seed_vectors[1], candidate_vector)

            # Max aggregation
            similarity_score = max(similarity_score_A, similarity_score_B)
        else:
            similarity_score = similarity_score_A

        return similarity_score


    # Filters tracks based on mood
    @staticmethod
    def _filter_mood(queryset, mood: str):
        if not mood:
            return queryset

        mood_score_service = MoodScoreService()
        queryset = mood_score_service.calculate_mood_score(queryset)

        # Filtering range is applied based on the mood
        #  Ex. Tracks with a mood score greater than 0.7 are considered if the user selected 'happy' mood, etc.
        if mood == "happy":
            return queryset.filter(mood_score__gt=0.7)
        if mood == "sad":
            return queryset.filter(mood_score__lt=0.4)
        return queryset.filter(mood_score__gte=0.4, mood_score__lte=0.7)

    # Filter the tracks based on genre and year
    def _create_genre_year_filters(self, user_preferences: Dict[str, Any]) -> Q:
        genres = self._coerce_genres(user_preferences.get("genres") or user_preferences.get("genre"))

        start_year = self._coerce_year(
            user_preferences.get("start_year") or user_preferences.get("era_start")
        )
        end_year = self._coerce_year(
            user_preferences.get("end_year") or user_preferences.get("era_end")
        )

        filters = Q()
        if genres:
            filters &= Q(genre__in=genres)
        if start_year is not None:
            filters &= Q(year__gte=start_year)
        if end_year is not None:
            filters &= Q(year__lte=end_year)

        return filters

    @staticmethod
    # Calculate the cosine similarity score between two vectors
    def _cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:

        norm_a = norm(vector_a)
        norm_b = norm(vector_b)

        if norm_a == 0 or norm_b == 0:
            # Zero vectors cannot be ranked by cosine similarity because the denominator
            # is zero. Treating them as similarity 0 keeps the recommender stable
            return 0.0

        cosine_score = np.dot(vector_a, vector_b) / (norm_a * norm_b)

        return cosine_score

    @staticmethod
    def _format_duration(duration_ms: int) -> str:
        total_seconds = int(round(duration_ms / 1000))
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def _track_payload(self, track: SpotifyTrack) -> Dict[str, Any]:
        return {
            "track_id": track.track_id,
            "track_name": track.track_name,
            "title": track.track_name,
            "artist_names": track.artist_name,
            "artist": track.artist_name,
            "duration_ms": track.duration_ms,
            "duration": self._format_duration(track.duration_ms),
            "genre": track.genre,
            "year": track.year,
        }


    def _track_payload_with_similarity(
        self, track: SpotifyTrack,
        similarity_score: float | None,
    ) -> Dict[str, Any]:
        payload = self._track_payload(track)
        payload["similarity_score"] = similarity_score
        return payload

  
    @staticmethod
    def _get_embedding_vector(embedding: SpotifyTrackEmbedding) -> List[float]:
        return [float(getattr(embedding, field)) for field in EMBEDDING_FIELDS]

    # Get the vector embeddings for the given track ids
    def _embedding_map(self, track_ids: Iterable[str]) -> Dict[str, List[float]]:
        embeddings = SpotifyTrackEmbedding.objects.filter(track_id__in=track_ids)
        return {
            embedding.track_id: self._get_embedding_vector(embedding)
            for embedding in embeddings
        }

    @staticmethod
    def _coerce_year(value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)
    
    @staticmethod
    def _coerce_genres(value: Any) -> List[str]:
        if value in (None, ""):
            return []
        if isinstance(value, str):
            return [value.lower()]
        return [str(genre).lower() for genre in value if str(genre).strip()]

    @staticmethod
    def _parse_preferences(user_preferences: Any) -> Dict[str, Any]:
        if isinstance(user_preferences, str):
            import json

            return json.loads(user_preferences)
        return dict(user_preferences or {})
