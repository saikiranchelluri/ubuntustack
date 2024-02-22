from django.urls import path
from users.views import userRegister,userLogin,Profile_Register,Questionnaire,Questionnaire_2,Questionnaire_3,\
        Questionnaire_4,Update_Phone_Number_View,Phone_Number_VerifyOTP_View,Resend_OTP_Phone_Number_View,register_email_View,Update_email_View,Generate_OTP_Update_Email_View,Update_Email_VerifyOTP,\
           Generate_OTP_2FA_VIew, Update_Two_FactAuth_View,VerifyOTP_twofactorauth,ResumeUploadView,Generate_OTP_Email_VIew,register_verifyotp,\
            my_profile,EditHobbiesAndInterests,EditSoftSkills,EditExperience,\
            EditEducation,EditCertifications,EditProfessionalAssociationAPI,Edit_Achievements_Accolades_API,ProgressAPI,logout_api,Selected_User_Journey,\
                ProfileImageUploadView,ProfileImageDeleteView,GetBasicDetails,UserUpdate,Update_communication_preferences,\
                    Update_account_integrations,GetAccountSettings,GetUserName,Password_Update_View,Update_Password_VerifyOTP,Generate_OTP_Update_Password_VIew,Intermediate_role,\
                        Runway_Recommendation,Selected_User_Journey,current_role,request_new_password_view,setup_newpassword_view, CheckIntermediateRole,PhoneCodes,Industry,Function,Career_Stream,\
                            CheckPasswordResetLink
   
   
   
urlpatterns = [

   path('v1/login/2fa/verify-otp/',VerifyOTP_twofactorauth.as_view(), name = 'VerifyOTP_twofactorauth'),
   path('v1/login/2fa/resend-otp/',Generate_OTP_2FA_VIew.as_view()),

    #update mobile number
   path('v1/account-settings/update-mobilenumber/',Update_Phone_Number_View.as_view()),
   path('v1/account-settings/mobilenumber/verify-otp/',Phone_Number_VerifyOTP_View.as_view()),
   path('v1/account-settings/mobilenumber/resend-otp/',Resend_OTP_Phone_Number_View.as_view()),
   
  #update password
   path('v1/account-settings/update-password/',Password_Update_View.as_view()),
    path('v1/account-settings/password/verify-otp/',Update_Password_VerifyOTP.as_view()),
    path('v1/account-settings/password/resend-otp/',Generate_OTP_Update_Password_VIew.as_view()),    

    #update email
   path('v1/account-settings/update-email/',Update_email_View.as_view(), name = 'email-otp'),
   path('v1/account-settings/email/verify-otp/',Update_Email_VerifyOTP.as_view()),
   path('v1/account-settings/email/resend-otp/',Generate_OTP_Update_Email_View.as_view()),

   #2FA
   path('v1/account-settings/update-2fa/',Update_Two_FactAuth_View.as_view(), name = 'Update_Two_FactAuth_View'),

   #Updated Endpoints
   path('v1/onboarding/email-verification/',register_email_View.as_view(), name = 'email-otp'), #for onboarding
   path('v1/onboarding/email-verification/verify-otp/',register_verifyotp.as_view(), name = 'register_verifyotp'),
   path('v1/onboarding/email-verification/resend-otp/',Generate_OTP_Email_VIew.as_view(), name = 'Generate_OTP_Email_VIew'),
   path('v1/onboarding/setup-password/', userRegister.as_view(),name = 'register'),

   path('v1/delete-account/<id>/', userRegister.as_view(),name = 'delete user'),
   
   path('v1/onboarding/setup-profile/', Profile_Register.as_view()),
   path('v1/onboarding/setup-profile/<user_id>/', Profile_Register.as_view()),
   path('v1/onboarding/upload-resume/', ResumeUploadView.as_view()),
   
   path('v1/onboarding/questionnaire-1/', Questionnaire.as_view()),
   path('v1/onboarding/questionnaire-1/<pk>/', Questionnaire.as_view()),

   path('v1/onboarding/questionnaire-2/', Questionnaire_2.as_view()),
   path('v1/onboarding/questionnaire-2/<pk>/', Questionnaire_2.as_view()),

   path('v1/onboarding/questionnaire-3/', Questionnaire_3.as_view()),
   path('v1/onboarding/questionnaire-3/<pk>/', Questionnaire_3.as_view()),

   path('v1/onboarding/questionnaire-4/', Questionnaire_4.as_view()),
   path('v1/onboarding/questionnaire-4/<pk>/', Questionnaire_4.as_view()),

   path('v1/onboarding/intermediate-role/', Intermediate_role.as_view()),
   path('v1/onboarding/intermediate-role/<pk>/', Intermediate_role.as_view()),

   path('v1/onboarding/check-intermediate/',CheckIntermediateRole.as_view()),

   path('v1/onboarding/runway-recommendation/<pk>/', Runway_Recommendation.as_view()),
   path('v1/onboarding/current-role/<pk>/', current_role.as_view()),

   path('v1/onboarding/selected-runway/',Selected_User_Journey.as_view()),
   path('v1/onboarding/selected-runway/<pk>/',Selected_User_Journey.as_view()),

   path('v1/onboarding/custom-runway/',Selected_User_Journey.as_view()),
   path('v1/onboarding/custom-runway/<pk>/',Selected_User_Journey.as_view()),

   path('v1/login/', userLogin.as_view(),name = 'login'),
   path('v1/logout/', logout_api.as_view(),name = 'logout'),
   
   path('v1/onboarding-progress/<id>/', ProgressAPI.as_view(),name = 'onboarding-progress'),
   
   
   # My PROFILE
   path('v1/my-profile/<id>/', my_profile.as_view(),name = 'my-profile'),
   path('v1/my-profile/hobbies/<pk>/', EditHobbiesAndInterests.as_view()),
   path('v1/my-profile/soft-skills/<pk>/', EditSoftSkills.as_view()),


   path('v1/my-profile/experience/<pk>/', EditExperience.as_view()),
   path('v1/my-profile/delete-experience/<pk>/<experience_id>/', EditExperience.as_view()),#to delete
   path('v1/my-profile/edit-experience/<pk>/<exp_id>/', EditExperience.as_view()),


   path('v1/my-profile/education/<pk>/', EditEducation.as_view()),
   path('v1/my-profile/delete-education/<pk>/<education_id>/', EditEducation.as_view()),#to delete
   path('v1/my-profile/edit-education/<pk>/<edu_id>/', EditEducation.as_view()),


   path('v1/my-profile/certifications/<pk>/', EditCertifications.as_view()),
   path('v1/my-profile/delete-certifications/<pk>/<certificate_id>/', EditCertifications.as_view()),#to delete
   path('v1/my-profile/edit-certifications/<pk>/<cert_id>/', EditCertifications.as_view()),


   path('v1/my-profile/professional-association/<pk>/', EditProfessionalAssociationAPI.as_view()),
   path('v1/my-profile/delete-professional-association/<pk>/<professional_id>/', EditProfessionalAssociationAPI.as_view()),#to delete
   path('v1/my-profile/edit-professional-association/<pk>/<prof_id>/', EditProfessionalAssociationAPI.as_view()),

   path('v1/my-profile/achievements/<pk>/', Edit_Achievements_Accolades_API.as_view()),#to get and post
   path('v1/my-profile/delete-achievements/<pk>/<achievement_id>/', Edit_Achievements_Accolades_API.as_view()),#to delete
   path('v1/my-profile/edit-achievements/<pk>/<ach_id>/', Edit_Achievements_Accolades_API.as_view()),# to edit
   

   #update image 
    
   path('v1/account-settings/update-profile-image/', ProfileImageUploadView.as_view(), name = 'image-upload'),
   path('v1/account-settings/delete-profile-image/<str:id>/', ProfileImageDeleteView.as_view(), name = 'image-delete'),


    #Account setting update method 
   path('v1/account-settings/update-personal-info/',UserUpdate.as_view()),
   path('v1/account-settings/update-communication-preferences/',Update_communication_preferences.as_view()),
   path('v1/account-settings/update-account-integrations/',Update_account_integrations.as_view()),
   path('v1/account-settings/',GetAccountSettings.as_view()), #fetching all the account details
   path('v1/account-settings/username/',GetUserName.as_view()), #fetching all the account details


   #Basic details
   path('v1/user/basic-details/',GetBasicDetails.as_view()),

   #Forgot password/Password reset
   path('v1/password-reset/request-new-password/',request_new_password_view.as_view()),
   path('v1/password-reset/setup-new-password/<uid>/<token>/',setup_newpassword_view.as_view()),
   path('v1/password-reset/check-reset-link/<uid>/<token>/',CheckPasswordResetLink.as_view()),
   path('v1/password-reset/resend-email/',request_new_password_view.as_view()),
   path('v1/dial-codes/',PhoneCodes.as_view()),
   path('v1/industries/',Industry.as_view()),
   path('v1/functions/',Function.as_view()),
   path('v1/career-stream/',Career_Stream.as_view()),
   path('v1/add-industries/<selected_industry>/<company_type_id/',Industry.as_view()),

]