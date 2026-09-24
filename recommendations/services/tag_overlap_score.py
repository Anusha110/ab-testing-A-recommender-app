
from typing import List, Any, Dict
from collections import defaultdict


class TagOverlapScoreService:

    def get_tag_overlap_score(
        self, candidate_track_id: str,
        candidate_track_id_wise_tag_ids: defaultdict[Any, list],
        seed_A_tag_wise_counts: dict[Any, Any], seed_B_tag_wise_counts: dict[Any, Any],
        tag_id_wise_details: dict[Any, Any]
    ) -> int | float:

        # Calculate the tag overlap score between the candidate track and seed Track A
        tag_overlap_score_A = self.calculate_tag_overlap_score(
            tag_ids=candidate_track_id_wise_tag_ids[candidate_track_id],
            candidate_tag_id_wise_details=tag_id_wise_details,
            seed_tag_wise_counts=seed_A_tag_wise_counts
        )

        # Calculate the tag overlap score between the candidate track and seed Track A
        if seed_B_tag_wise_counts:
            tag_overlap_score_B = self.calculate_tag_overlap_score(
                tag_ids=candidate_track_id_wise_tag_ids[candidate_track_id],
                candidate_tag_id_wise_details=tag_id_wise_details,
                seed_tag_wise_counts=seed_B_tag_wise_counts
            )

            # Consider the maximum tag overlap score as the final score
            tag_overlap_score = max(tag_overlap_score_A, tag_overlap_score_B)
        else:
            # Since, there's one seed Track A, consider this as the final score
            tag_overlap_score = tag_overlap_score_A

        return tag_overlap_score


    @staticmethod
    def calculate_tag_overlap_score(
            tag_ids: List[str], candidate_tag_id_wise_details: Dict,
            seed_tag_wise_counts: Dict):

        tag_overlap_count = 0
        total_tag_count = 0

        # Loop over every tag_id that belongs to the candidate
        # If the seed Track has the same tag_id, we can add the tag's count to the total.
        for tag_id in tag_ids:

            tag_details = candidate_tag_id_wise_details[tag_id]
            tag_name = tag_details["tag_name"]
            tag_count = tag_details["tag_count"]

            # Check if the seed track has the same tag and get it's count.
            seed_tag_count = seed_tag_wise_counts.get(tag_name, 0)

            # Tag counts can be less than 0 if user's downvotes a tag. We only consider tags that are upvoted, i.e. tags that are actually relevant.
            if seed_tag_count > 0 and tag_count > 0:
                tag_overlap_count += tag_count

            if tag_count > 0:
                total_tag_count += tag_count

        # if the candidate does not have any tags, then the score is 0.
        if total_tag_count == 0:
            tag_overlap_score = 0
        else:
            # The final score is the percentage of the candidate's tags, that the seed Track also shares/matches.
            tag_overlap_score = tag_overlap_count / total_tag_count

        return tag_overlap_score