def get_user_ip(request):    
    '''This function fetches the IP address of the user'''    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')    
    if x_forwarded_for:        
        ip = x_forwarded_for.split(',')[0]    
    else:        
        ip = request.META.get('REMOTE_ADDR')    
        return ip