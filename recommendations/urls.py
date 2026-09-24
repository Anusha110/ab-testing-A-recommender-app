from django.urls import path
from recommendations.views import Recommendations, SearchTracks

urlpatterns = [
    path('', Recommendations.as_view() , name="recommendations"),
    path('search/', SearchTracks.as_view(), name="search_tracks")
]