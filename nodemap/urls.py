from django.urls import path
from nodemap.views import Nodemap,Edit_CE_View,Edit_Action_Title_Validation_View,\
    Edit_Action_View,EditIntermediate,ValidateIntermediate,Validate_Action_title_View,Add_Action_View,\
    Validate_Milestone_title_View,Update_Milestone_View,GetEntryToPlace,Add_Intermediate,Add_Milestone_View,Add_Milestone_validate_title_View,\
        Add_Milestone_Path_view,EditNorthStar,Validate_AddIntermediate,Milestone_Progress__View,Critical_Enablers

urlpatterns = [
    path('v1/nodemap/get-data/<pk>/',Nodemap.as_view()),
    path('v1/nodemap/edit-ce/<id>/',Edit_CE_View.as_view()),
    path('v1/nodemap/edit-action/validate-title/',Edit_Action_Title_Validation_View.as_view()),
    path('v1/nodemap/edit-action/<id>/',Edit_Action_View.as_view()),

    path('v1/nodemap/validate-intermediate/',ValidateIntermediate.as_view()),
    path('v1/nodemap/edit-intermediate/<id>/',EditIntermediate.as_view()),
    path('v1/nodemap/get-entry/<id>/',GetEntryToPlace.as_view()),
    path('v1/nodemap/add-intermediate/validate-title/',Validate_AddIntermediate.as_view()),
    path('v1/nodemap/add-intermediate/',Add_Intermediate.as_view()),
    path('v1/nodemap/edit-north-star/<id>/',EditNorthStar.as_view()),

    path('v1/nodemap/add-action/validate-title/',Validate_Action_title_View.as_view()),    
    path('v1/nodemap/add-action/',Add_Action_View.as_view()),
    path('v1/nodemap/milestone/validate-title/',Validate_Milestone_title_View.as_view()),
    path('v1/nodemap/edit-milestone/<id>/',Update_Milestone_View.as_view()),
    path('v1/nodemap/add-milestone/validate-title/',Add_Milestone_validate_title_View.as_view()),
    path('v1/nodemap/add-milestone/place-after/<id>/',Add_Milestone_Path_view.as_view()),
    path('v1/nodemap/add-milestone/',Add_Milestone_View.as_view()),
    path('v1/nodemap/milestone-progress/<id>/',Milestone_Progress__View.as_view()),
    path('v1/nodemap/critical-enablers/',Critical_Enablers.as_view()),

]