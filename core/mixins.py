from users.mongoDb_connection import nudge_preference as np_collection, users_registration

from bson.objectid import ObjectId

from datetime import datetime

# Functions

nudge_type_mapping = {
    1: 'milestones',
    2: 'actions',
    3: 'critical_enablers',
    4: 'recommendations',
    # Add more mappings as needed
}

def nudge_preference(user_id):

    data = {
        "milestones" : {
            "nudge_type" : 1,
            "email_notification" : False,
            "web_notification" : False,
            "updated_on" : datetime.now()
        },
        "actions" : {
            "nudge_type" : 2,
            "email_notification" : False,
            "web_notification" : False,
            "updated_on" : datetime.now()
        },
        "critical_enablers" : {
            "nudge_type" : 3,
            "email_notification" : False,
            "web_notification" : False,
            "updated_on" : datetime.now()
        },
        "recommendations" : {
            "nudge_type" : 4,
            "email_notification" : False,
            "web_notification" : False,
            "updated_on" : datetime.now()
        }

    }
    
    np_collection.insert_one(
        {
        "user_id" : str(user_id),
        "nudge_preference" : data,
        "created_on" : datetime.now()
        }
    )

    return f"Nudge Preference Added successfully for the user : {user_id}"