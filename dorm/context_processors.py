def global_context(request):
    """
    Makes the user's profile and household available on all templates.
    """
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            household = profile.household
            return {
                'user_profile': profile,
                'household': household
            }
        except:
            pass # Fails gracefully if no profile
    
    return {} # Return empty dict