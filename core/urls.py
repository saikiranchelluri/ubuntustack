from django.urls import path
from core.views import Search_Filter,Resources,NudgePreferenceView,SearchByKeywords,Tags

urlpatterns = [

#search
   
   path('v1/resources/',Resources.as_view()),
   path('v1/get-resources/',Resources.as_view()),
   path('v1/update-resource/<id>/',Resources.as_view()),
   path('v1/search/',Search_Filter.as_view()),
   path('v1/personalized-recommendatons/<pk>/',SearchByKeywords.as_view()),
   path('v1/filter/',Search_Filter.as_view()),
   path('v1/delete-resource/<id>/', Resources.as_view(),name = 'delete resource'),
   path('nudge-preference/<user_id>/',NudgePreferenceView.as_view()),
   path('v1/get-tags/',Tags.as_view()),
   
   


]