import pymongo
import environ
from pymongo import MongoClient
import urllib

env = environ.Env()
environ.Env.read_env()
environment=env('ENV')

if environment=='LOCAL':
    client = pymongo.MongoClient("mongodb://localhost:27017/")
else:
    mongodb_user_name=str(env('MONGODB_USERNAME')).strip()
    password=str(env('MONGODB_PASSWORD')).strip()
    mongodb_pass_word=urllib.parse.quote(password)
    #print("mongodb_pass_word:",mongodb_pass_word)
    mongodb_host=str(env('MONGODB_HOST')).strip()
    mongodb_port=int(env('MONGODB_PORT'))
    mongodb_db_name=str(env('MONGODB_DBNAME')).strip()
    client = MongoClient(f'mongodb://{mongodb_user_name}:{mongodb_pass_word}@{mongodb_host}:{mongodb_port}/{mongodb_db_name}')


db=client['ProjectMomentum']
users_registration=db['users']
userLogin_Details=db['userlogin_details']
resume_data=db['profile']
dashboard_data = db['roadmap']
billing_details=db['billing']
plan_details = db['plans']
resources=db['resources']
nudges=db['nudge']
nudge_preference=db['nudge_preferences']
payments_collection=db['payments']
phone_codes=db['dial_codes']
industry=db['industries']
function=db['functions']
Reason=db["roadmap_update_reasons"]
critical_enablers = db['critical_enablers']
subscriptions_collection = db['subscriptions']
youechatbot_collection=db['chat_conversations']
Cost_Details=db["user_gpt_usage_costs"]