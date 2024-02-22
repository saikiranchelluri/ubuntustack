from django.urls import path
from payments.views import Create_Checkout_Session, stripe_webhook, Invoice_PDF_View, Send_Invoice_Email, \
    Update_Auto_Renewal_View, Transaction_History, Success_View, Cancel_View,Current_Plan,GetPlanDetails,\
    Update_Subscription,Price_Details

urlpatterns = [
path('payment/success/', Success_View.as_view(), name='success'),
    path('payment/failure/', Cancel_View.as_view(), name='cancel'),
    path('v1/payments/create-checkout-session/', Create_Checkout_Session.as_view(), name='create-checkout-session'),
    path('v1/payments/stripe-webhook/', stripe_webhook, name='stripe-webhook'),
    path('v1/payments/download-invoice/<str:invoice_id>/', Invoice_PDF_View.as_view(), name='invoice-pdf-view'),
    path('v1/payments/email-invoice/', Send_Invoice_Email.as_view(), name='send-invoice-email'),
    path('v1/payments/update-auto-renewal/', Update_Auto_Renewal_View.as_view(), name='update-auto-renewal'),
    path('v1/payments/transaction-history/<str:user_id>/', Transaction_History.as_view(), name='transaction-history'),
    path('v1/payments/current-plan/<str:user_id>/', Current_Plan.as_view(), name='current-plan'),
    path('v1/payments/plan-details/', GetPlanDetails.as_view(), name='get-plan'),
    path('v1/prices/', Price_Details.as_view(), name='price-details'),#this API is for landing page
    path('v1/payments/update-subscription/', Update_Subscription.as_view(), name='update-subscription'),
]