# from datetime import datetime, timedelta
from datetime import datetime, timedelta

import stripe
from bson import ObjectId
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse

from youe_backend import settings
from users.mongoDb_connection import subscriptions_collection, payments_collection, plan_details



# def get_stripe_price_id_from_invoice(invoice_id):
#     stripe.api_key = settings.STRIPE_SECRET_KEY # Replace with your Stripe secret key
#
#     try:
#         # Retrieve the invoice from Stripe using its ID
#         invoice = stripe.Invoice.retrieve(invoice_id)
#
#         # Extract the price_id from the invoice's line items
#         if invoice.lines and len(invoice.lines.data) > 0:
#             for line_item in invoice.lines.data:
#                 price_id = line_item.price.id
#                 print("price_id:", price_id)
#
#                 # Find the plan that contains the specified price_id
#                 plan = plan_details.find_one({"prices.stripe_payment_price_id": price_id})
#                 print("stripe_payment_price_id:", plan)
#
#                 if plan:
#                     # Get the correct stripe_price_id from the matching price document
#                     for price in plan['prices']:
#                         if price['stripe_payment_price_id'] == price_id:
#                             stripe_price_id = price['stripe_price_id']
#                             print("stripe_price_id from plan:", stripe_price_id)
#                             return stripe_price_id
#
#                     print("No matching stripe_price_id found in the plan.")
#                     return None
#                 else:
#                     return None
#
#         print("No matching price_id found in the invoice.")
#         return None
#
#     except stripe.error.InvalidRequestError as e:
#         print(f"Error retrieving invoice: {e}")
#         return None


def get_stripe_price_id_from_invoice(invoice_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY # Replace with your Stripe secret key

    try:
        # Retrieve the invoice from Stripe using its ID
        invoice = stripe.Invoice.retrieve(invoice_id)

        # Extract the price_id from the invoice's line items
        if invoice.lines and len(invoice.lines.data) > 0:
            for line_item in invoice.lines.data:
                price_id = line_item.price.id
                print("price_id:", price_id)

                # Find the plan that contains the specified price_id
                plan = plan_details.find_one({"prices.stripe_payment_price_id": price_id})
                print("stripe_payment_price_id:", plan)

                if plan:
                    # Get the correct stripe_price_id from the matching price document
                    for price in plan['prices']:
                        if price['stripe_payment_price_id'] == price_id:
                            stripe_price_id = price['stripe_price_id']
                            print("stripe_price_id from plan:", stripe_price_id)
                            return stripe_price_id

                    print("No matching stripe_price_id found in the plan.")
                    return None
                else:
                    return None

        print("No matching price_id found in the invoice.")
        return None

    except stripe.error.InvalidRequestError as e:
        print(f"Error retrieving invoice: {e}")
        return None


def handle_checkout_completed(event):
    session = event['data']['object']
    user_id = session.get('metadata', {}).get('user_id')
    plan_id = session.get('metadata', {}).get('plan_id')

    # Retrieve plan data using plan_id
    plan_data = plan_details.find_one({"_id": ObjectId(plan_id)})

    # Rest of the code remains the same
    product_id = session.get('metadata', {}).get('product_id')
    plan_name = session.get('metadata', {}).get('product_name')
    service = session.get('metadata', {}).get('service')
    currency_symbol = session.get('metadata', {}).get('currency_symbol')
    payment_status = session['payment_status']
    subscription_id = session.get('subscription', None)
    customer_details = session.get('customer_details', {})
    customer_address = customer_details.get('address', {})
    customer_mobile = customer_details.get('mobile', None)
    total_details = session.get('total_details', {})
    amount_discount = total_details.get('amount_discount')

    address_data = {
        "city": customer_address.get('city'),
        "country": customer_address.get('country'),
        "line1": customer_address.get('line1'),
        "line2": customer_address.get('line2'),
        "postal_code": customer_address.get('postal_code'),
        "state": customer_address.get('state')
    }

    # Remove empty values
    address_data = {k: v for k, v in address_data.items() if v is not None}

    customer_id = session['customer']
    payment_method = session.get('payment_method_types', [])[0]
    invoice_id = session['invoice']
    payment_intent_id = (
                event['data']['object'].get('payment_intent') or
                stripe.Invoice.retrieve(event['data']['object']['invoice']).payment_intent
        )

        # Retrieve payment_intent to get payment_method
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    payment_intent_method = payment_intent.payment_method


        # Retrieve payment_method details
    payment_method_details = stripe.PaymentMethod.retrieve(payment_intent_method)

    payment_method_id = payment_method_details.id
    print("payment_method_id",payment_method_id)
    # # Update payment method details directly in Stripe
    # stripe.Customer.modify(
    #     customer_id,
    #     invoice_settings={
    #         'default_payment_method': payment_method_id
    #     }
    # )

    if payment_method_details.type == 'card':
        # Extract card details if the payment method is a card
        card_details = {
            "last4": payment_method_details.card.last4,
            "brand": payment_method_details.card.brand,
            "type": payment_method_details.card.funding,
        }
        print("Card Details:", card_details)
    else:
        # Set card details to null or any other appropriate value
        card_details = None
        print("This payment method is not a card.")
    if amount_discount is not None and amount_discount != 0:
        discount = amount_discount / 100
    else:
        # No discount needed
        discount = 0



    payments_data = {
        "user_id": user_id,
        "plan_id": plan_id,
        "plan_name": plan_name,
        "stripe_product_id": product_id,
        "customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "invoice_id": invoice_id,
        "payment_date": datetime.now(),
        "paid_amount": session['amount_total'] / 100,
        "discount": discount,
        "actual_amount": session['amount_subtotal'] / 100,
        "currency": session['currency'],
        "currency_symbol": currency_symbol,
        "service": service,
        "status": payment_status,
        "payment_intent_id":payment_intent_id,
        "payment_method": payment_method_details.type,

        "address_data": address_data,
        "card_details":card_details,
        "customer_mobile_number": customer_mobile,
        "created_at": datetime.now()
    }

    if payments_collection.find_one({"payment_intent_id": payment_intent_id}):
        unpaid_invoice_data = payments_collection.find_one({"payment_intent_id": payment_intent_id, "status": "failed"})
        print("hello")
        if unpaid_invoice_data:
            if session['mode'] == 'payment':
                if session['mode'] == 'payment':

                    print("Entered payment mode")
                    if payments_collection.find_one({"payment_intent_id": payment_intent_id, "status": "paid"}):
                        return HttpResponse(status=200)
                    else:

                        try:
                            recurring = get_stripe_price_id_from_invoice(invoice_id)
                            print("recurring", recurring)

                            # Retrieve subscription schedules
                            schedules = stripe.SubscriptionSchedule.list(customer=customer_id).data

                            # Check if there is an active schedule without cancel status
                            existing_active_schedule = next((schedule for schedule in schedules if
                                                             schedule.get('status') == 'not_started' and schedule.get(
                                                                 'end_behavior') != 'cancel'), None)

                            if existing_active_schedule:
                                # If an active schedule without cancel status exists, do not create a new one
                                return HttpResponse(status=200)

                            # Initialize existing_end_date outside the if-else block
                            existing_end_date = None

                            # Check if there are any canceled schedules
                            canceled_schedules = [schedule for schedule in schedules if
                                                  schedule.get('end_behavior') == 'cancel']

                            if canceled_schedules:
                                # Use the end date of the last canceled schedule as the start date
                                last_canceled_schedule = max(canceled_schedules, key=lambda x: x.get('created'))
                                existing_end_date = datetime.fromtimestamp(
                                    last_canceled_schedule['phases'][-1]['end_date'])
                            else:
                                # If no canceled schedules, retrieve active subscriptions
                                subscriptions = stripe.Subscription.list(customer=customer_id, status='active', limit=1,
                                                                         expand=['data.default_payment_method'])

                                if subscriptions.data:
                                    # Take the end date of the first active subscription as the start date
                                    existing_end_date = datetime.fromtimestamp(subscriptions.data[0].current_period_end)

                            # Check if there are schedules before creating the start_dates set
                            if schedules:
                                # Check if today's date is already a start date in existing schedules
                                start_dates = {datetime.fromtimestamp(phase['start_date']).date() for schedule in
                                               schedules for
                                               phase in
                                               schedule.get('phases', []) if 'start_date' in phase}
                            else:
                                start_dates = set()

                            # Ensure only one schedule is created, and start date is not duplicated
                            if existing_end_date and existing_end_date.date() not in start_dates:
                                stripe.SubscriptionSchedule.create(
                                    customer=customer_id,
                                    start_date=int(existing_end_date.timestamp()),
                                    end_behavior='release',
                                    phases=[
                                        {
                                            'items': [
                                                {
                                                    'price': recurring,
                                                    'quantity': 1
                                                }
                                            ],
                                            'trial_end': int((existing_end_date + timedelta(days=365)).timestamp())
                                        }
                                    ],
                                )
                                print("failed checkout")

                            return HttpResponse(status=200)

                        except stripe.error.StripeError as e:
                            # Handle Stripe API errors here
                            print(f"Stripe API Error: {e}")
                            return None

                return HttpResponse(status=200)

        return HttpResponse(status=200)


    if session['mode'] == 'subscription':
        if payments_collection.find_one({"payment_intent_id": payment_intent_id, "status": "paid"}):
            return HttpResponse(status=200)
        payment_result = payments_collection.insert_one(payments_data)
        # If no subscription record exists, insert a new one
        start_date=datetime.now()
        end_date=start_date+relativedelta(years=1)
        subscription_data = {
            "user_id": user_id,
            "plan_id": plan_id,
            "payments_id": payment_result.inserted_id,
            "subscription_id": subscription_id,
            "customer_id": customer_id,
            "status": "active",
            "payment_date": datetime.now(),
            "start_at": datetime.now(),
            "end_at": end_date,
            "auto_renew": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        subscriptions_collection.insert_one(subscription_data)
        return HttpResponse(status=200)
    if session['mode'] == 'payment':
        print("Entered payment mode")
        if payments_collection.find_one({"payment_intent_id": payment_intent_id, "status": "paid"}):
            return HttpResponse(status=200)
        else:


            # Insert payment data into the collection
            payment_result = payments_collection.insert_one(payments_data)
            payment_id = payment_result.inserted_id

            try:
                recurring = get_stripe_price_id_from_invoice(invoice_id)
                print("checkout_recurring", recurring)

                # Retrieve subscription schedules
                schedules = stripe.SubscriptionSchedule.list(customer=customer_id).data

                # Check if there is an active schedule without cancel status
                existing_active_schedule = next((schedule for schedule in schedules if
                                                 schedule.get('status') == 'not_started' and schedule.get(
                                                     'end_behavior') != 'cancel'), None)

                if existing_active_schedule:
                    # If an active schedule without cancel status exists, do not create a new one
                    return HttpResponse(status=200)

                # Initialize existing_end_date outside the if-else block
                existing_end_date = None

                # Check if there are any canceled schedules
                canceled_schedules = [schedule for schedule in schedules if
                                      schedule.get('end_behavior') == 'cancel']
                print("canceled_schedules",canceled_schedules)

                if canceled_schedules:
                    # Use the end date of the last canceled schedule as the start date
                    last_canceled_schedule = max(canceled_schedules, key=lambda x: x.get('created'))
                    existing_end_date = datetime.fromtimestamp(last_canceled_schedule['phases'][-1]['end_date'])
                    print("existing_end_date", existing_end_date)
                else:
                    # If no canceled schedules, retrieve active subscriptions
                    subscriptions = stripe.Subscription.list(customer=customer_id, status='active', limit=1,
                                                             expand=['data.default_payment_method'])

                    if subscriptions.data:
                        # Take the end date of the first active subscription as the start date
                        existing_end_date = datetime.fromtimestamp(subscriptions.data[0].current_period_end)

                # Check if there are schedules before creating the start_dates set
                if schedules:
                    # Check if today's date is already a start date in existing schedules
                    start_dates = {datetime.fromtimestamp(phase['start_date']).date() for schedule in schedules for
                                   phase in
                                   schedule.get('phases', []) if 'start_date' in phase}
                else:
                    start_dates = set()
                print("ceckout sceduling")
                # Ensure only one schedule is created, and start date is not duplicated
                if existing_end_date  and existing_end_date.date() not in start_dates:
                    stripe.SubscriptionSchedule.create(
                        customer=customer_id,
                        start_date=int(existing_end_date.timestamp()),
                        end_behavior='release',
                        phases=[
                            {
                                'items': [
                                    {
                                        'price': recurring,
                                        'quantity': 1
                                    }
                                ],
                                'trial_end': int((existing_end_date + timedelta(days=365)).timestamp())
                            }
                        ],
                    )
                    print("checkout")

                return HttpResponse(status=200)

            except stripe.error.StripeError as e:
                # Handle Stripe API errors here
                print(f"Stripe API Error: {e}")
                return None

    return HttpResponse(status=200)


def handle_subscription_updated(event):
    subscription = event['data']['object']
    subscription_id = subscription['id']
    cancel_at_period_end = subscription['cancel_at_period_end']

    if not cancel_at_period_end:
        return HttpResponse(status=200)  # Do nothing if cancel_at_period_end is False

    # Extract cancel_date from subscription
    cancel_date = datetime.fromtimestamp(subscription['current_period_end'])

    # Update the corresponding database record with the cancel date
    subscriptions_collection.update_one(
        {"subscription_id": subscription_id},
        {"$set": {"updated_at": datetime.now()}},
    )

    return HttpResponse(status=200)
#
def handle_invoice_payment_succeeded(event):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    invoice = event['data']['object']
    #print("invoice",invoice)

    subscription_id = invoice['subscription']
    #print("subscription_id",subscription_id)
    # print("subscription_id",subscription_id)

    payment_intent_id = invoice['payment_intent']
    if payment_intent_id is None:
        return HttpResponse(status=200)
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    #print("payment_intent",payment_intent)
    payment_method = payment_intent.payment_method
    #print(" invoice_payment_method ", payment_method )

    # Retrieve payment_method details
    payment_method_details = stripe.PaymentMethod.retrieve(payment_method)
    customer_id=invoice['customer']


    if payment_method_details.type == 'card':
        # Extract card details if the payment method is a card
        card_details = {
            "last4": payment_method_details.card.last4,
            "brand": payment_method_details.card.brand,
            "type": payment_method_details.card.funding,
        }
        #print("Card Details:", card_details)
    else:
        # Set card details to null or any other appropriate value
        card_details = None
        #print("This payment method is not a card.")

    invoice_number = invoice["id"]
    print("invoice_number",invoice_number)
    if payments_collection.find_one({"invoice_id": invoice_number, "status": "paid"}):
        return HttpResponse(status=200)

    existing_payment_record = payments_collection.find_one({"invoice_id": invoice_number,"status":"paid"})
    stripe_price_type = invoice['lines']['data'][0]['price']['type']
    print("invoice...stripe_price_type", stripe_price_type)

    if existing_payment_record:
        # Update the payment_intent_id and status in the existing document

        payments_collection.update_one(
            {"invoice_id": invoice_number},
            {
                "$set": {
                    "payment_intent_id": payment_intent_id,
                    # "status": invoice['status']  # Replace with the actual updated status
                }
            }
        )
        return HttpResponse(status=200)

        # Extract relevant information from the invoice
    stripe_price_id = invoice['lines']['data'][0]['price']['id']
    stripe_price_type = invoice['lines']['data'][0]['price']['type']
    print("stripe_price_type", stripe_price_type)
    price_currency = invoice['lines']['data'][0]['price']['currency']
    price_document = plan_details.find_one({
        "prices.stripe_price_id": stripe_price_id
    })
    print("stripe_price_id", stripe_price_id)




    # Initialize variables
    service = None
    plan_name = None
    product_id = None
    plan_id = None
    currency_symbol = None
    price_id=None
    recurring_price_id=None

    # Check if the document is found
    if price_document:
        service = price_document["service"]
        product_id = price_document["product_id"]
        plan_name = price_document["plan"]
        plan_id = price_document["_id"]
        price_id=stripe_price_id

        # Search for the plan details
        for price_info in price_document["prices"]:
            if price_info["stripe_price_id"] == stripe_price_id:
                currency_symbol = price_info.get("currency_symbol")
                break  # No need to continue searching once found
            if price_info["stripe_payment_price_id"] == stripe_price_id:
                currency_symbol = price_info.get("currency_symbol")
                recurring_price_id= price_info.get("stripe_price_id")
                break

    # Extract customer_id and subscription_id
    customer_id = invoice['customer']
    subscription_id = invoice['subscription']
    # Assuming 'invoice' contains the invoice data
    customer_address = invoice.get("customer_address")

    total_discount_amounts = invoice.get("total_discount_amounts", [])
    total_discount_amount = sum(discount.get("amount", 0) for discount in total_discount_amounts) / 100

    address_data = {}

    if customer_address is not None:
        address_data = {
            "city": customer_address.get('city'),
            "country": customer_address.get('country'),
            "line1": customer_address.get('line1'),
            "line2": customer_address.get('line2'),
            "postal_code": customer_address.get('postal_code'),
            "state": customer_address.get('state')
        }

    # Remove empty values
    address_data = {k: v for k, v in address_data.items() if v is not None}
    payments_data = {
        "user_id": customer_id,
        "plan_id": plan_id,
        "plan_name": plan_name,
        "stripe_product_id": product_id,
        "customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "invoice_id": invoice['id'],
        "payment_date": datetime.now(),
        "paid_amount": invoice['amount_paid'] / 100,
        "discount": total_discount_amount,
        "actual_amount": invoice['amount_due'] / 100,
        "currency": price_currency,
        "currency_symbol": currency_symbol,
        "service": service,
        "status": invoice['status'],
        "payment_intent_id": invoice['payment_intent'],
        "payment_method": payment_method_details.type,  # Assuming payment is via Stripe
        "card_details": card_details,

        "payment_details": address_data,

        "customer_mobile_number": "",  # Add customer's mobile number if available
        "created_at": datetime.now()
    }
    if not existing_payment_record:
        stripe.api_key = settings.STRIPE_SECRET_KEY

        if stripe_price_type == 'recurring':
            subscription = stripe.Subscription.retrieve(subscription_id)

            if (

                        subscription['items']['data'][0]['price']['recurring']['interval'] == 'year'

                ):

                    if payments_collection.find_one({"payment_intent_id": payment_intent_id, "status": "paid"}):
                        return HttpResponse(status=200)
                    else:


                        payment_result = payments_collection.insert_one(payments_data)
                        if subscriptions_collection.find_one({"subscription_id": subscription_id}):
                            subscription_record=subscriptions_collection.find_one({"subscription_id": subscription_id})
                            end_at = subscription_record.get("end_at")
                            new_start_date = datetime.now()
                            new_end_date = end_at + relativedelta(years=1)

                            # Update subscription details
                            subscriptions_collection.update_one(
                                {"subscription_id": subscription_id},
                                {
                                    "$set": {

                                        "payments_id": payment_result.inserted_id,
                                        "status": "active",

                                        "end_at": new_end_date,
                                        "payment_date": new_start_date,
                                        "auto_renew": True,
                                        "updated_at": datetime.now()
                                    }
                                }
                            )

                        else:


                            start_date = datetime.now()
                            new_end_date = start_date + relativedelta(years=1)

                            subscription_data = {
                                "user_id": customer_id,
                                "plan_id": plan_id,
                                "payments_id": payment_result.inserted_id,
                                "subscription_id": subscription_id,
                                "customer_id": customer_id,
                                "status": "active",  # Set initial status as active
                                "payment_date": start_date,
                                "start_at": start_date,  # Set start date as the current date/time
                                "end_at": new_end_date,  # End date will be updated when the subscription ends
                                "auto_renew": True,  # Adjust as needed based on your logic
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            }

                            subscriptions_collection.insert_one(subscription_data)

                            return HttpResponse(status=200)
                        return HttpResponse(status=200)


        if stripe_price_type=='one_time':
            if payments_collection.find_one({"payment_intent_id": payment_intent_id, "status": "paid"}):
                return HttpResponse(status=200)
            else:

                payment_result = payments_collection.insert_one(payments_data)
                payment_id = payment_result.inserted_id

                try:
                    recurring = get_stripe_price_id_from_invoice(invoice_number)
                    print("recurring", recurring)

                    # Retrieve subscription schedules
                    schedules = stripe.SubscriptionSchedule.list(customer=customer_id).data

                    # Check if there is an active schedule without cancel status
                    existing_active_schedule = next((schedule for schedule in schedules if
                                                     schedule.get('status') == 'not_started' and schedule.get(
                                                         'end_behavior') != 'cancel'), None)

                    # if existing_active_schedule:
                    #     # If an active schedule without cancel status exists, do not create a new one
                    #     return HttpResponse(status=200)

                    # Initialize existing_end_date outside the if-else block
                    existing_end_date = None

                    # Check if there are any canceled schedules
                    canceled_schedules = [schedule for schedule in schedules if
                                          schedule.get('end_behavior') == 'cancel']

                    if canceled_schedules:
                        # Use the end date of the last canceled schedule as the start date
                        last_canceled_schedule = max(canceled_schedules, key=lambda x: x.get('created'))
                        existing_end_date = datetime.fromtimestamp(last_canceled_schedule['phases'][-1]['end_date'])
                    else:
                        # If no canceled schedules, retrieve active subscriptions
                        subscriptions = stripe.Subscription.list(customer=customer_id, status='active', limit=1,
                                                                 expand=['data.default_payment_method'])

                        if subscriptions.data:
                            # Take the end date of the first active subscription as the start date
                            existing_end_date = datetime.fromtimestamp(subscriptions.data[0].current_period_end)

                    # Check if there are schedules before creating the start_dates set
                    if schedules:
                        # Check if today's date is already a start date in existing schedules
                        start_dates = {datetime.fromtimestamp(phase['start_date']).date() for schedule in schedules for
                                       phase in
                                       schedule.get('phases', []) if 'start_date' in phase}
                    else:
                        start_dates = set()

                    # Ensure only one schedule is created, and start date is not duplicated
                    if existing_end_date and existing_end_date.date() not in start_dates:
                        stripe.SubscriptionSchedule.create(
                            customer=customer_id,
                            start_date=int(existing_end_date.timestamp()),
                            end_behavior='release',
                            phases=[
                                {
                                    'items': [
                                        {
                                            'price': recurring,
                                            'quantity': 1
                                        }
                                    ],
                                    'trial_end': int((existing_end_date + timedelta(days=365)).timestamp())
                                }
                            ],
                        )
                        print("invoice")

                    return HttpResponse(status=200)

                except stripe.error.StripeError as e:
                    # Handle Stripe API errors here
                    print(f"Stripe API Error: {e}")
                    return None

        return HttpResponse(status=200)


    return HttpResponse(status=200)


def handle_invoice_payment_failed(event):
    invoice = event['data']['object']
    print("failed_invoice", invoice)
    # Extract relevant information from the invoice
    stripe_price_id = invoice['lines']['data'][0]['price']['id']
    price_currency = invoice['lines']['data'][0]['price']['currency']
    price_document = plan_details.find_one({
        "prices.stripe_price_id": stripe_price_id
    })
    payment_intent_id = invoice['payment_intent']
    invoice_id = invoice['id']

    # Check if a payment with the same invoice ID or payment intent ID already exists
    existing_payment = payments_collection.find_one({
        "$or": [
            {"invoice_id": invoice_id},
            {"payment_intent_id": payment_intent_id}
        ]
    })

    if existing_payment:
        return HttpResponse(status=200)

    # Initialize variables
    service = None
    plan_name = None
    product_id = None
    collection_id = None

    # Check if the document is found
    if price_document:
        service = price_document["service"]
        product_id = price_document["product_id"]
        plan_name = price_document["plan"]
        collection_id = price_document["_id"]

        # Search for the plan details
        for price_info in price_document["prices"]:
            if price_info["stripe_price_id"] == stripe_price_id:
                break  # No need to continue searching once found

    # Extract customer_id and subscription_id
    customer_id = invoice['customer']
    subscription_id = invoice['subscription']

    payments_data = {
        "user_id": customer_id,
        "plan_id": collection_id,  # Replace with the actual plan ID
        "plan_name": plan_name,  # Replace with the actual plan name
        "stripe_product_id": product_id,
        "customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "invoice_id": invoice['id'],
        "payment_date": datetime.now(),
        "paid_amount": invoice['amount_paid'] / 100,  # Assuming amount is in cents
        "discount": 0,  # You can replace this with the actual discount amount if available
        "actual_amount": invoice['amount_due'] / 100,  # Assuming amount is in cents
        "currency": invoice['currency'],
        # "currency_symbol": currency_symbol,  # Assuming you have this value available
        "service": service,
        "status": 'failed',
        "payment_intent_id": invoice['payment_intent'],
        "payment_method": "card",  # Assuming payment is via Stripe
        "payment_details": {
            "city": invoice['customer_address']['city'],
            "country": invoice['customer_address']['country'],
            "line1": invoice['customer_address']['line1'],
            "line2": invoice['customer_address']['line2'],
            "postal_code": invoice['customer_address']['postal_code'],
            "state": invoice['customer_address']['state']
        },
        "customer_mobile_number": "",  # Add customer's mobile number if available
        "created_at": datetime.now()
    }

    # Insert payment data into the payments collection
    payment_result = payments_collection.insert_one(payments_data)

    # Update subscription details
    subscriptions_collection.update_one(
        {"subscription_id": subscription_id},
        {
            "$set": {
                "payments_id": payment_result.inserted_id,
                "status": "expired",
                "auto_renew": False,
                "updated_at": datetime.now(),

            }
        }
    )

def handle_payment_intent_failed(event):
    failed = event['data']['object']

    if 'last_payment_error' in failed and 'payment_method' in failed['last_payment_error']:

        user_id = failed['customer']

        plan_id = None
        plan_name = None
        product_id = None
        subscription_id = None
        invoice_id = failed['invoice']
        amount_discount = None
        payment_intent_id = failed['id']
        payment_method = failed['last_payment_error']['payment_method']['type']
        billing_details = failed['last_payment_error']['payment_method']['billing_details']
        address_data = {
            "city": billing_details.get('address', {}).get('city'),
            "country": billing_details.get('address', {}).get('country'),
            "line1": billing_details.get('address', {}).get('line1'),
            "line2": billing_details.get('address', {}).get('line2'),
            "postal_code": billing_details.get('address', {}).get('postal_code'),
            "state": billing_details.get('address', {}).get('state')
        }
        address_data = {k: v for k, v in address_data.items() if v is not None}
        phone = billing_details.get('phone')
        email = billing_details.get('email')
        currency_symbol = None  # You'll need to retrieve this based on the currency code
        payments_data = {

            "user_id": user_id, "plan_id": plan_id, "plan_name": plan_name, "stripe_product_id": product_id,
            "customer_id": user_id,  # Using user_id as customer_id
            "stripe_subscription_id": subscription_id, "invoice_id": invoice_id, "payment_date": datetime.now(),
            "paid_amount": failed['amount_received'] / 100, "discount": amount_discount,
            "actual_amount": failed['amount'] / 100,  # Convert from cents to dollars
            "currency": failed['currency'], "currency_symbol": currency_symbol, "service": 'youe subscription',
            # You'll need to define the 'service'
            "status": 'failed', "payment_intent_id": payment_intent_id, "payment_method": payment_method,
            "payment_details": address_data,
            "customer_mobile_number": phone, "created_at": datetime.now()
        }
        payments_collection.insert_one(payments_data)

        return HttpResponse(status=200)
    else:
        return HttpResponse(status=200)

def handle_subscription_deleted(event):
    subscription_id = event['data']['object']['id']
    # Find and update the subscription in MongoDB
    subscriptions_collection.update_one(
        {'subscription_id': subscription_id},
        {'$set': {'status': 'expired'}},
    )
from datetime import datetime
from bson.objectid import ObjectId

def handle_subscription_schedule(event):
    schedule = event['data']['object']
    customer_id = schedule['customer']
    schedule_id = schedule['id']
    trial_end_date = schedule['phases'][0]['trial_end']  # Accessing trial end date correctly

    existing_schedules = stripe.SubscriptionSchedule.list(customer=customer_id).data

    active_schedule = None
    for existing_schedule in existing_schedules:
        if existing_schedule.get('end_behavior') == 'release':
            if active_schedule is None or existing_schedule.get('created') > active_schedule.get('created'):
                active_schedule = existing_schedule

    if active_schedule is not None and active_schedule['id'] == schedule_id:
        subscriptions_collection.update_many(
            {"customer_id": customer_id},
            {
                "$set": {
                    "subscription_id": schedule_id,
                    "payment_date": datetime.now(),
                    "end_at": datetime.utcfromtimestamp(trial_end_date),
                    "auto_renew": True,
                    "status": "active",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            }
        )

        # Find the latest payment record for the customer with "paid" status
        latest_paid_payment = payments_collection.find_one(
            {"customer_id": customer_id, "status": "paid"},
            sort=[("created_at", -1)]  # Sorting to get the latest payment record
        )
        active_schedule = None

        release_schedule_ids = []

        # Identify active schedule and collect 'release' schedules
        for existing_schedule in existing_schedules:
            if existing_schedule['id'] == schedule_id:
                active_schedule = existing_schedule
                print("active_schedule", active_schedule)
            elif existing_schedule.get('end_behavior') == 'release':
                release_schedule_ids.append(existing_schedule['id'])
                print("release_schedule_ids", release_schedule_ids)

        # Modify 'release' schedules to end behavior 'cancel' if not updated
        for release_schedule_id in release_schedule_ids:
            idd=subscriptions_collection.find_one({"subscription_id": release_schedule_id})
            print("idddddd",idd)
            if not idd:
                try:
                    stripe.SubscriptionSchedule.cancel(release_schedule_id)

                except stripe.error.StripeError as e:
                    # Handle Stripe API errors here
                    print(f"Stripe API Error: {e}")
                    return None


        if latest_paid_payment:
            latest_payment_id = latest_paid_payment['_id']
            # Update the payment collection with the new subscription ID and updated_at field
            payments_collection.update_one(
                {"_id": ObjectId(latest_payment_id)},
                {
                    "$set": {
                        "stripe_subscription_id": schedule_id,
                        "updated_at": datetime.now()
                    }
                }
            )
            subscriptions_collection.update_many(
                {"customer_id": customer_id},
                {
                    "$set": {

                        "payments_id": latest_payment_id,

                    }
                }
            )



            # Assuming you're using Django, you should return an HTTP response
            return HttpResponse(status=200)
        else:
            # If no paid payment record is found, handle the case as required
            return HttpResponse(status=400)  # Or handle this case as required
    else:
        # If the last subscription is not the one being updated, do something else or return an error
        return HttpResponse(status=400)  # Or handle this case as required
def handle_refund_event(event):
    print(event)
    payment_intent_id = event['data']['object']['payment_intent']
    print("payment_intent_id",payment_intent_id)
    refunded_amount = event['data']['object']
    print("refunded_amount", refunded_amount)
    updated_payment =payments_collection.update_one(
        {'payment_intent_id': payment_intent_id},
        {'$set': {'status': 'refunded'}}
    )
    return HttpResponse(status=200)
    # record_id = updated_payment['_id']
    # print(f"Payment record {record_id} updated to 'refunded'")
    # subscription = subscriptions_collection.find_one({'payments_id': record_id})
    # subscription_id=subscription["subscription_id"]
    # print("subscription_id",subscription_id)
    #
    # if subscription:
    #     # Update the status to 'expired' in subscription_collection
    #     subscriptions_collection.update_one(
    #         {'payments_id':record_id},
    #         {'$set': {'status': 'expired'}}
    #     )


