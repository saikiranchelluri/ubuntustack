import redis
redis_host = 'localhost' # Use the appropriate Redis hostname or IP address here
redis_port = 6379
redis_db = 3
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)


#connection for update mobile number
redis_db_update_number = 4
redis_client_update_number = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db_update_number)

#update Email
redis_db_update_email = 5
redis_client_update_email = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db_update_email)
#update password
redis_db_update_password = 6
redis_client_update_password = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db_update_password)
#2FA
redis_db_update_2FA = 7
redis_client_update_2FA = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db_update_2FA)
