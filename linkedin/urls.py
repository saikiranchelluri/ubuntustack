from django.urls import path
from linkedin.views import LinkedinAuthorizationUrl,LinkedinSignUpAPI,LinkedinSigninAPI




urlpatterns = [
    path('v1/linkedin-auth-url/', LinkedinAuthorizationUrl.as_view()),
    path('v1/linkedin-signup/', LinkedinSignUpAPI.as_view()),
    path('v1/linkedin-signin/', LinkedinSigninAPI.as_view()),
    # path('v1/linkedin-retrive/<id>/', LinkedinRetriev.as_view()),
]