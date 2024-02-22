from django.shortcuts import render
import base64
from users.utils import onboarding_status_fun,calculate_redirect_step
import os
import time
from payments.stripe_events import handle_checkout_completed, handle_subscription_updated, \
    handle_invoice_payment_succeeded, handle_invoice_payment_failed,\
    handle_payment_intent_failed,handle_subscription_deleted, handle_subscription_schedule,handle_refund_event
import requests
from bson import ObjectId
from dateutil.relativedelta import relativedelta
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from youe_backend import settings
import stripe

from payments.utils import get_user_ip
from users.mongoDb_connection import users_registration,  plan_details,payments_collection, \
    subscriptions_collection

from youe_backend.settings import base_url

'''success view for stripe checkout'''
class Success_View(View):
    def get(self, request):
        return render(request, 'sucess.html')

'''cancel view for stripe checkout'''

class Cancel_View(View):
    def get(self, request):
        return render(request, 'cancel.html')

'''checkout API for payments'''

# Initialize Stripe API with secret key
stripe.api_key = settings.STRIPE_SECRET_KEY

class Create_Checkout_Session(APIView):
    def post(self, request):
        try:
            # Retrieve user_id and plan_id from request data
            user_id = request.data.get('user_id')
            plan_id = request.data.get('plan_id')

            # Check if user_id and plan_id are provided
            if not user_id or not plan_id:
                return Response({'message': 'User id or plan id not provided'}, status=status.HTTP_400_BAD_REQUEST)

            # Retrieve user information from the database
            user = users_registration.find_one({"_id": ObjectId(user_id)})
            if not user:
                return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
            onboarding_status=user["onboarding_process"]["step"]
            onboarding_step= onboarding_status_fun(onboarding_status)
            user_email = user.get('email')

            # Retrieve plan details from the database
            plan_data = plan_details.find_one({"_id": ObjectId(plan_id)})
            if not plan_data:
                return Response({'message': 'Plan not found'}, status=status.HTTP_400_BAD_REQUEST)
            if onboarding_status!=8:
                    return Response(
                        {"message": "Please complete the onboarding process",
                        "user_id":str(user_id),
                        "onboarding_status":onboarding_step},
                        status=status.HTTP_200_OK)

            # Extract relevant information from plan_data
            product_id = plan_data['product_id']
            service = plan_data['service']
            product_name = plan_data['plan']

            # Retrieve user's IP address for location-based pricing
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            url = 'http://ip-api.com/json/' + str(ip)
            get_req = requests.get(url)
            response = get_req.json()
            country = response.get('country', ' ')

            # Initialize variables for pricing information
            price_id = None
            coupon = None
            currency_symbol = None
            stripe_payment_price_id = None

            # Iterate through price_info to find matching country
            for price_info in plan_data['prices']:
                if country == price_info['country']:
                    price_id = price_info['stripe_price_id']
                    coupon = price_info['stripe_coupon']
                    currency_symbol = price_info['currency_symbol']
                    stripe_payment_price_id = price_info['stripe_payment_price_id']
                    break

            # If no matching country is found, default to 'United States'
            if not price_id:
                for price_info in plan_data['prices']:
                    if price_info['country'] == 'United States':
                        price_id = price_info['stripe_price_id']
                        coupon = price_info['stripe_coupon']
                        currency_symbol = price_info['currency_symbol']
                        stripe_payment_price_id = price_info['stripe_payment_price_id']
                        break

            # Determine success and cancel URLs based on domain
            domain = request.META['HTTP_HOST']
            if domain == "127.0.0.1:8000":
                success_url = 'http://localhost:8000/payment/success'
                cancel_url = 'http://localhost:8000/payment/failure'
            else:
                success_url = f'{base_url}/payment/success'
                cancel_url = f'{base_url}/payment/failure'

            # Attempt to retrieve the customer from Stripe
            try:
                customer = stripe.Customer.retrieve(user_id)
            except stripe.error.InvalidRequestError:
                customer = None

            # If customer doesn't exist, create it
            if not customer:
                customer = stripe.Customer.create(
                    id=user_id,
                    email=user_email
                )

                # Create a subscription with discount for the first time
                checkout_session = stripe.checkout.Session.create(
                    mode='subscription',
                    line_items=[{
                        'price': price_id,
                        'quantity': 1,
                    }],
                    discounts=[{
                        'coupon': coupon,
                    }],
                    success_url=success_url,
                    cancel_url=cancel_url,
                    metadata={'plan_id': plan_id, 'user_id': user_id, 'product_id': product_id,
                              'product_name': product_name, 'service': service,
                              'currency_symbol': currency_symbol},
                    customer=user_id
                )

                return Response({'payment_link': checkout_session.url,
                                 'country': country,
                                 'ip': str(ip)},
                                status=status.HTTP_200_OK)

            # Retrieve existing subscriptions for the customer
            subscriptions = stripe.Subscription.list(customer=user_id)

            if subscriptions['data']:
                last_subscription = subscriptions['data'][0]
                #print("last_subscription",last_subscription)


                if last_subscription['status'] == 'active':
                    if last_subscription['cancel_at_period_end'] is True:
                        # Create a checkout session for payment

                        checkout_session = stripe.checkout.Session.create(
                            mode='payment',
                            line_items=[{
                                'price': stripe_payment_price_id,
                                'quantity': 1,
                            }],
                            success_url=success_url,
                            cancel_url=cancel_url,
                            metadata={'plan_id': plan_id, 'user_id': user_id, 'product_id': product_id,
                                      'product_name': product_name, 'service': service,
                                      'currency_symbol': currency_symbol},
                            customer=user_id,
                            invoice_creation={
                                "enabled": True}
                        )

                        return Response({'payment_link': checkout_session.url,
                                         'country': country,
                                         'ip': str(ip)},
                                        status=status.HTTP_200_OK)
                    else:

                            return Response({'message': 'Your current subscription is active'},
                                            status=status.HTTP_400_BAD_REQUEST)
                if last_subscription['status'] == 'incomplete':
                        # If the last subscription status is 'incomplete'
                        user_subscription = subscriptions_collection.find_one({'user_id': user_id})
                        discount = [] if user_subscription else [{'coupon': coupon}]

                        checkout_session = stripe.checkout.Session.create(
                            mode='subscription',
                            line_items=[{
                                'price': price_id,
                                'quantity': 1,
                            }],
                            discounts=discount,
                            # discounts=[{
                            #     'coupon': coupon,
                            # }],
                            success_url=success_url,
                            cancel_url=cancel_url,
                            metadata={'plan_id': plan_id, 'user_id': user_id, 'product_id': product_id,
                                      'product_name': product_name, 'service': service,
                                      'currency_symbol': currency_symbol},
                            customer=user_id,

                        )

                        return Response({'payment_link': checkout_session.url,
                                         'country': country,
                                         'ip': str(ip)},
                                        status=status.HTTP_200_OK)
                if last_subscription['status'] == 'trialing':
                    end_date = datetime.utcfromtimestamp(last_subscription['current_period_end']).strftime(
                        '%d-%m-%Y')
                    #print("end_date", end_date)

                    # Provide end date only if the last subscription is in a trial period
                    return Response(
                        {'message': f'Your current subscription  is active until {end_date}'},
                        status=status.HTTP_200_OK)

                # else:
                #         return Response({'message': 'Last subscription is not canceled yet.'},
                #                         status=status.HTTP_400_BAD_REQUEST)
                # else:
                #     return Response({'message': f'Your current subscription is active until {end_date}'},
                #                     status=status.HTTP_400_BAD_REQUEST)
            else:
                    #Create a checkout session for subscription renewal
                    user_subscription = subscriptions_collection.find_one({'user_id': user_id})
                    discount = [] if user_subscription else [{'coupon': coupon}]

                    checkout_session = stripe.checkout.Session.create(
                        mode='subscription',
                        line_items=[{
                            'price': price_id,
                            'quantity': 1,
                        }],
                        discounts=discount,
                        success_url=success_url,
                        cancel_url=cancel_url,
                        metadata={'plan_id': plan_id, 'user_id': user_id, 'product_id': product_id,
                                  'product_name': product_name, 'service': service,
                                  'currency_symbol': currency_symbol},
                        customer=user_id
                    )

                    return Response({'payment_link': checkout_session.url,
                                     'country': country,
                                     'ip': str(ip)},
                                    status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            return Response({"message": "A Stripe error occurred", 'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"message": "An error occurred", 'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"message": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from datetime import datetime, timedelta

'''webhooks for payments status and id's '''

from rest_framework.decorators import api_view
@csrf_exempt
@api_view(['POST'])
def stripe_webhook(request):
    from datetime import datetime
    payload = request.body
    signature = request.META['HTTP_STRIPE_SIGNATURE']
    event = None
    webhook_secret=settings.STRIPE_WEBHOOK_SECRET
    try:
         event = stripe.Webhook.construct_event(
             payload=request.body,
             sig_header=signature,
             secret=webhook_secret
         )


    except ValueError as e:
         return Response(str(e),status=400)
    except stripe.error.SignatureVerificationError as e:
          return Response(str(e),status=400)
    if event['type'] == 'checkout.session.completed':
        handle_checkout_completed(event)



    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event)

    elif event['type'] == 'invoice.payment_succeeded':

        handle_invoice_payment_succeeded(event)

    elif event['type'] == 'payment_intent.payment_failed':

        handle_payment_intent_failed(event)

    elif event['type']=='invoice.payment_failed':
        handle_invoice_payment_failed(event)

    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event)
    elif event['type'] == 'subscription_schedule.created':
        handle_subscription_schedule(event)
    elif event['type'] == 'charge.refund.updated':
        handle_refund_event(event)


    return HttpResponse(status=200)


'''payments invoice in pdf format'''


class Invoice_PDF_View(APIView):
    def get(self, request, invoice_id):
        try:
            if invoice_id:
                invoice = payments_collection.find_one({"invoice_id": invoice_id})
                if invoice:
                    stripe.api_key = settings.STRIPE_SECRET_KEY
                    invoice = stripe.Invoice.retrieve(invoice_id)
                    response = invoice.hosted_invoice_url
                    return Response({"invoice": response})
                return Response({"message": "Invoice id not found"}, status=400)
            return Response({"message": "Invoice id not provided"}, status=400)
        except stripe.error.StripeError as e:
            return Response({"message": "An error occurred", 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

'''invoice to send an emails '''


class Send_Invoice_Email(APIView):
    def post(self, request):
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY


            invoice_id = request.data['invoice_id']
            user_id = request.data.get('user_id')
            invoice = payments_collection.find_one({"invoice_id": invoice_id})

            if not invoice:
                return Response({"message": "Invoice id not found"}, status=status.HTTP_400_BAD_REQUEST)

            user_record = users_registration.find_one({"_id": ObjectId(user_id)})

            if not user_record:
                return Response({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

            invoice = stripe.Invoice.retrieve(invoice_id)

            # Get the Price ID associated with the invoice
            price_id = invoice.lines.data[0].price.id  # Assuming there is one line item in the invoice

            # Retrieve the Price details from Stripe
            price = stripe.Price.retrieve(price_id)

            # Get the Product ID associated with the Price
            product_id = price.product

            # Retrieve the Product information using the Product ID
            product = stripe.Product.retrieve(product_id)
            product_name = product.name

            user_record = users_registration.find_one({"_id": ObjectId(user_id)})
            #print("user_record", user_record)
            user_email = user_record.get('email')
            #print("user_email", user_email)

            subject = 'Invoice'

            attachment_url = invoice.invoice_pdf
            attachment_content = requests.get(attachment_url).content

            email = EmailMessage(
                subject=subject,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email],
            )

            attachment_filename = "invoice.pdf"

            email.attach(attachment_filename, attachment_content, 'application/pdf')
            message = f"Dear Customer,\n\nHere is the invoice attached for the {product_name}. Thank you for choosing our services."
            #print("message", message)

            # Add text content within the email's body
            email.body = message

            email.send()

            return Response({"message": "Invoice email sent successfully."})

        except stripe.error.StripeError as e:
            return Response({"message":"an error occurred",'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Update_Auto_Renewal_View(APIView):
    def post(self, request):
        subscription_id = request.data.get('subscription_id')
        auto_renewal = request.data.get('auto_renew', False)

        # Check if subscription_id exists in the database
        subscription = subscriptions_collection.find_one({"subscription_id": subscription_id})
        if not subscription:
            return Response({'message': 'Subscription id not found'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            try:
                # Attempt to retrieve the subscription
                subscription = stripe.Subscription.retrieve(subscription_id)

                if auto_renewal == 'false':
                    if subscription:
                        # Modify subscription to cancel at the period end
                        updated_subscription = stripe.Subscription.modify(
                            subscription_id,
                            cancel_at_period_end=True
                        )

                        # Update subscription in the collection
                        subscriptions_collection.update_one(
                            {'subscription_id': subscription_id},
                            {'$set': {'auto_renew': False}}
                        )

                        return Response({"message": "Subscription successfully updated"},
                                        status=status.HTTP_200_OK)
                    else:
                        return Response({"message": "Invalid subscription ID"},
                                        status=status.HTTP_404_NOT_FOUND)

            except stripe.error.InvalidRequestError:
                # If Subscription retrieval fails, attempt to retrieve Subscription Schedule
                subscription_schedule = stripe.SubscriptionSchedule.retrieve(subscription_id)
                if subscription_schedule:
                    # Modify subscription schedule to end behavior 'cancel'
                    updated_schedule = stripe.SubscriptionSchedule.modify(
                        subscription_id,
                        end_behavior='cancel'
                    )

                    # Update subscription in the collection if needed for schedule
                    subscriptions_collection.update_one(
                        {'subscription_id': subscription_id},
                        {'$set': {'auto_renew': False}}
                    )

                    return Response({"message": "Subscription  successfully updated"},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({"message": "Invalid subscription  ID"},
                                    status=status.HTTP_404_NOT_FOUND)

        except stripe.error.StripeError as e:
            return Response({"message": "An error occurred", "error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Update_Subscription(APIView):
    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        subscription_id = request.data.get('subscription_id')
        subscription_status = request.data.get('status', 'active')

        try:
            try:
                # Attempt to retrieve the subscription
                subscription = stripe.Subscription.retrieve(subscription_id)

                if subscription_status == 'canceled':
                    if subscription:
                        # Modify subscription to cancel at the period end
                        updated_subscription = stripe.Subscription.modify(
                            subscription_id,
                            cancel_at_period_end=True
                        )

                        # Update subscription in the collection
                        subscriptions_collection.update_one(
                            {'subscription_id': subscription_id},
                            {'$set': {'auto_renew': False, 'status': 'canceled'}}
                        )

                        return Response({"message": "Subscription successfully updated"},
                                        status=status.HTTP_200_OK)
                    else:
                        return Response({"message": "Invalid subscription ID"},
                                        status=status.HTTP_404_NOT_FOUND)

            except stripe.error.InvalidRequestError:
                # If Subscription retrieval fails, attempt to retrieve Subscription Schedule
                subscription_schedule = stripe.SubscriptionSchedule.retrieve(subscription_id)
                if subscription_schedule:
                    # Modify subscription schedule to end behavior 'cancel'
                    updated_schedule = stripe.SubscriptionSchedule.modify(
                        subscription_id,
                        end_behavior='cancel'
                    )

                    # Update subscription in the collection if needed for schedule
                    subscriptions_collection.update_one(
                        {'subscription_id': subscription_id},
                        {'$set': {'auto_renew': False, 'status': 'canceled'}}
                    )

                    return Response({"message": "Subscription  successfully updated"},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({"message": "Invalid subscription  ID"},
                                    status=status.HTTP_404_NOT_FOUND)

        except stripe.error.StripeError as e:
            return Response({"message": "An error occurred", "error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from datetime import datetime


class Transaction_History(APIView):

    def get_invoice_info(self, invoice_id):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            invoice_number = invoice.number
            return invoice_number
        except stripe.error.InvalidRequestError as e:
            # Handle the case where the invoice ID is invalid or not found
            return None

    def convert_payment_date(self, payment_date):
        if payment_date is not None:
            formatted_payment_date = payment_date.strftime('%d/%m/%y')
            return formatted_payment_date
        return None

    def get(self, request, user_id):
        try:
            user = users_registration.find_one({"_id": ObjectId(user_id)})
            if not user:
                return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

            transactions = payments_collection.find({"user_id": user_id})
            transaction_data = list(transactions)

            if transaction_data:
                formatted_transactions = []
                for transaction in transaction_data:
                    transaction['_id'] = str(transaction['_id'])

                    payment_date = transaction.get('payment_date')
                    plan_name=transaction.get('plan_name')
                    formatted_payment_date = self.convert_payment_date(payment_date)

                    invoice_id = transaction.get('invoice_id')

                    service=transaction.get('service')

                    invoice_number = self.get_invoice_info(invoice_id)

                    formatted_transactions.append({
                        'payment_date': formatted_payment_date,

                        'invoice_id': invoice_id,
                        'invoice_number': invoice_number,
                        'service':service,

                    })

                return Response({"transaction_history": formatted_transactions})
            else:
                return Response({'message': 'No transactions found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"message":"An error occurred",'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from datetime import datetime, timezone

class Current_Plan(APIView):
    def convert_payment_date(self, end_date):
        if end_date is not None:
            formatted_payment_date = end_date.strftime('%d/%m/%y')
            return formatted_payment_date
        return None
    def get(self, request, user_id):
        from datetime import datetime
        current_date = datetime.now()

        # Check if user_id exists in the database
        user = users_registration.find_one({"_id": ObjectId(user_id)})
        if not user:
            return Response({'message': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

        subscription = subscriptions_collection.find_one({
            "user_id": user_id,
            "start_at": {"$lte": current_date},
            "end_at": {"$gte": current_date}
        })

        if not subscription:
            return Response({'message': 'No active subscriptions found for this user.'}, status=status.HTTP_400_BAD_REQUEST)

        plan_data = subscription.get("plan_id")
        plan = plan_details.find_one({"_id": ObjectId(plan_data)})

        if not plan:
            return Response({'message': 'Plan details not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the latest payment record for this subscription
        payment = payments_collection.find({
            "stripe_subscription_id": subscription.get("subscription_id")
        }).sort([("created_at", -1)]).limit(1)


        payment = payment[0]  # Get the first (latest) payment record

        currency = payment.get("currency").upper()
        currency_symbol = payment.get("currency_symbol")
        paid_amount = payment.get("paid_amount")
        discount = payment.get("discount")
        end_date = subscription.get("end_at")
        formatted_end_date = self.convert_payment_date(end_date)

        response_data = {

            "plan_name": plan.get("plan"),
            "features": plan.get("features"),
            "paid_amount": paid_amount,
            "discount": discount,
            "currency": currency,
            "currency_symbol": currency_symbol,
            "subscription_id": subscription.get("subscription_id"),
            "auto_renew": subscription.get("auto_renew"),
            "subscription_status": subscription.get("status"),
            "end_at": formatted_end_date
        }

        return Response(response_data, status=status.HTTP_200_OK)




class GetPlanDetails(APIView):
    def get(self, request):
        try:
            user_id = request.query_params.get("id")
            if not user_id:
                return Response({"message": "User ID not provided"}, status=status.HTTP_400_BAD_REQUEST)
            plan_data = plan_details.find_one()

            if plan_data:
                ip = self.get_client_ip(request)
                #print(ip)
                url = 'http://ip-api.com/json/' + str(ip)  # 35.212.99.153 #157.51.78.54 #101.112.0.0 #118.26.105.0

                get_req = requests.get(url)
                #print("get_req:", get_req)

                response = get_req.json()
                #print("response:", response)
                user_country_code = response.get('countryCode', ' ')
                #print("User Country_code:", user_country_code)
                # Retrieve user's country-specific price from the "prices" list in the plan document
                user_price_document = None
                for price_info in plan_data.get("prices", []):
                    if price_info.get("country_code") == user_country_code:
                        user_price_document = price_info
                        #print("User_price_document:", user_price_document)
                        break
                if not user_price_document:
                    # Use USA price as a fallback
                    for price_info in plan_data.get("prices", []):
                        if price_info.get("country_code") == "US":
                            user_price_document = price_info
                            #print("User_price_document:", user_price_document)
                            break

                if user_price_document:
                    user_country = user_price_document["country"]
                    user_actual_price = user_price_document["actual_annual_price"]
                    user_discount_price = user_price_document["discount"]
                    user_countrycode = user_price_document["country_code"]
                    user_discounted_price = user_price_document["final_annual_price"]
                    user_currency = user_price_document["currency"]
                    user_currency_symbol = user_price_document["currency_symbol"]                
                    #annual_price = user_price_document.get("actual_yearly_price", 0)
                    #monthly_price = round(annual_price / 12,2)  
                    
                    # Construct the response data
                    response_data = {
                        "user_id" : user_id,
                        "plan_id":str(plan_data["_id"]),
                        "plan":plan_data["plan"],
                        "features": plan_data["features"],
                        "country" : user_country,
                        "country_code":user_countrycode,
                        "actual_annual_price":user_actual_price,
                        "discount" : user_discount_price,
                        "final_annual_price":user_discounted_price,
                        "currency":user_currency,
                        "currency_symbol" : user_currency_symbol
                        #"monthly_price" : monthly_price
                    }

                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    return Response({"message": f"Price not available for {user_country_code}"},
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({"message": "Plan not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "An error occurred","error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class Price_Details(APIView):
    def get(self, request):
        try:
            plan_data = plan_details.find_one()

            if plan_data:
                ip = self.get_client_ip(request)
                #print(ip)
                url = 'http://ip-api.com/json/' + str(ip)  # 35.212.99.153 #157.51.78.54 #101.112.0.0 #118.26.105.0

                get_req = requests.get(url)
                #print("get_req:", get_req)

                response = get_req.json()
                #print("response:", response)
                user_country_code = response.get('countryCode', ' ')
                #print("User Country_code:", user_country_code)
                # Retrieve user's country-specific price from the "prices" list in the plan document
                user_price_document = None
                for price_info in plan_data.get("prices", []):
                    if price_info.get("country_code") == user_country_code:
                        user_price_document = price_info
                        #print("User_price_document:", user_price_document)
                        break
                if not user_price_document:
                    # Use USA price as a fallback
                    for price_info in plan_data.get("prices", []):
                        if price_info.get("country_code") == "US":
                            user_price_document = price_info
                            #print("User_price_document:", user_price_document)
                            break

                if user_price_document:
                    final_annual_price = user_price_document["final_annual_price"]
                    user_actual_price = user_price_document["actual_annual_price"]
                    currency_symbol = user_price_document["currency_symbol"]
                    user_discount_price = user_price_document["discount"]
                    user_currency = user_price_document["currency"]


                    # Construct the response data
                    response_data = {

                        "plan": plan_data["plan"],
                        "currency_symbol":currency_symbol,

                        "actual_annual_price": user_actual_price,
                        "discount": user_discount_price,
                        "final_annual_price":final_annual_price,
                        "currency": user_currency,

                    }

                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    return Response({"message": f"Price not available for {user_country_code}"},
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({"message": "Plan not found"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message":"an error occurred",'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip