from enum import Enum


class Mood(Enum):
    HAPPY = "Happy"
    SAD = "Sad"
    NEURAL = "Neutral"

    def get_list_of_values(self):
        return ["Happy", "Sad", "Neutral"]
