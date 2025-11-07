from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from .models import Household, UserProfile, Chore, Expense, ExpenseSplit, GroceryItem, GuestLog, Announcement
from .forms import SignUpForm, AnnouncementForm,UpdateHouseholdForm,EditProfileForm, CreateHouseholdForm, JoinHouseholdForm, GroceryItemForm, ChoreForm, ExpenseForm, GuestLogForm
from functools import wraps
import decimal
from django.db.models import Sum, Q
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.contrib import messages

# --------------------
# Authentication Views
# --------------------


# --- ADD THIS DECORATOR ---
# A decorator is a function that wraps another function
# to add extra behavior.
def household_required(view_func):
    """
    Decorator to check if a user is part of a household.
    If not, it redirects them to the household management page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user has a profile and a household
        try:
            profile = request.user.profile
            if profile.household is None:
                # If no household, redirect to the management page
                return redirect('household_management')
        except UserProfile.DoesNotExist:
            # If no profile, also redirect
             return redirect('household_management')
        
        # If they have a household, proceed with the original view
        return view_func(request, *args, **kwargs)
    return _wrapped_view


class CustomLoginView(auth_views.LoginView):
    template_name = 'dorm/login.html'

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save() # This saves the User AND creates the UserProfile
            login(request, user) # Log the new user in
            return redirect('home') # Redirect to the dashboard
    else:
        form = SignUpForm()
        
    return render(request, 'dorm/signup.html', {'form': form})

# Helper function to get the user's household
def get_user_household(request):
    try:
        profile = request.user.profile
        return profile, profile.household
    except UserProfile.DoesNotExist:
        return None, None

# --------------------
# Core App Views
# --------------------

# --- REPLACE YOUR CORE VIEWS WITH THESE ---


@login_required
@household_required
def home_view(request):
    profile, household = get_user_household(request)
    context = {}

    if household:
        # --- (NEW) Personal Action Items ---
        my_pending_chores = Chore.objects.filter(
            household=household,
            is_completed=False,
            assigned_to=request.user
        ).order_by('due_date')

        my_unsettled_debts = ExpenseSplit.objects.filter(
            owed_by=request.user,
            is_settled=False
        ).exclude(expense__paid_by=request.user).order_by('expense__date_paid') # <-- FIXED
        
        # --- (EXISTING) Household Overview ---
        all_pending_chores = Chore.objects.filter(household=household, is_completed=False)
        grocery_items = GroceryItem.objects.filter(household=household, is_purchased=False)
        recent_expenses = Expense.objects.filter(household=household).order_by('-date_paid')[:2]
        latest_announcement = Announcement.objects.filter(household=household).order_by('-created_at').first()
        
        balance = profile.get_balance()
        if balance > 0:
            balance_message = f"You are owed ₹{abs(balance):.2f}"
        elif balance < 0:
            balance_message = f"You owe ₹{abs(balance):.2f}"
        else:
            balance_message = "You are all settled up"
        
        context = {
            # New Personal Items
            'my_pending_chores': my_pending_chores,
            'my_unsettled_debts': my_unsettled_debts,
            
            # Existing Overview Items
            'balance': balance,
            'balance_message': balance_message,
            'pending_chore_count': all_pending_chores.count(),
            'grocery_item_count': grocery_items.count(),
            'upcoming_chores': all_pending_chores.order_by('due_date')[:2], # Renamed from pending_chores
            'recent_expenses': recent_expenses,
            'latest_announcement': latest_announcement,
        }
    
    return render(request, 'dorm/home.html', context)

@login_required
@household_required
def chores_view(request):
    profile, household = get_user_household(request)
    
    if request.method == 'POST':
        if 'add-chore' in request.POST:
            form = ChoreForm(request.POST, household=household)
            if form.is_valid():
                chore = form.save(commit=False)
                chore.household = household
                chore.created_by = request.user
                chore.save()
                messages.success(request, f"{request.user.profile.display_name} added a New Chore: {chore.title}")
                return redirect('chores')
        
        # --- (NEW) "MARK AS DONE" LOGIC ---
        elif 'mark-done' in request.POST:
            chore_id = request.POST.get('chore-id')
            chore = get_object_or_404(
                Chore, 
                id=chore_id, 
                household=household, 
                assigned_to=request.user # Only the assigned user can mark it done
            )
            chore.is_completed = True
            chore.save()
            return redirect('chores')
    
    chore_form = ChoreForm(household=household) 
    
    context = {
        'my_chores': Chore.objects.filter(household=household, assigned_to=request.user, is_completed=False).order_by('due_date'),
        'all_chores': Chore.objects.filter(household=household, is_completed=False).order_by('due_date'),
        'form': chore_form,
    }
    return render(request, 'dorm/chores.html', context)

# ... (add this new view)
@login_required
def settle_expense_view(request, pk):
    """
    Marks an ExpenseSplit as settled.
    'pk' is the ID of the ExpenseSplit, not the Expense.
    """
    # Only allow POST requests
    if request.method == 'POST':
        # Get the specific debt split
        split = get_object_or_404(ExpenseSplit, pk=pk)
        
        # Security Check:
        # Only the person who OWES or the person who PAID
        # can mark this as settled.
        if request.user == split.owed_by or request.user == split.expense.paid_by:
            split.is_settled = True
            split.save()
            
    return redirect('expenses')


# --- (REPLACE) Your entire expenses_view with this ---
@login_required
@household_required
def expenses_view(request):
    profile, household = get_user_household(request)
    
    if request.method == 'POST' and 'add-expense' in request.POST:
        # ... (Your existing form-saving logic is perfect) ...
        form = ExpenseForm(request.POST, household=household)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.household = household
            expense.paid_by = request.user
            expense.save() 
            messages.success(request, f"{request.user.profile.display_name} added a New Expense: {expense.title}")

            selected_users = form.cleaned_data['split_with']
            member_count = selected_users.count()
            if member_count > 0:
                split_amount = (expense.amount / decimal.Decimal(member_count)).quantize(decimal.Decimal('0.01'))
                for user in selected_users:
                    ExpenseSplit.objects.create(expense=expense, owed_by=user, amount_owed=split_amount)
            return redirect('expenses')
    
    expense_form = ExpenseForm(household=household)
    balance = profile.get_balance()
    
    # (NEW) Calculate total user has paid this month (for the new card)
    total_paid_result = Expense.objects.filter(
        household=household, 
        paid_by=request.user
    ).aggregate(total=Sum('amount'))
    total_you_paid = total_paid_result['total'] or decimal.Decimal(0)

    # Get "What You Owe" (unsettled)
    my_debts = ExpenseSplit.objects.filter(
        owed_by=request.user,
        is_settled=False
    ).exclude(expense__paid_by=request.user).order_by('-expense__date_paid')
    
    # Get "What You Are Owed" (unsettled)
    my_credits = ExpenseSplit.objects.filter(
        expense__paid_by=request.user,
        is_settled=False
    ).exclude(owed_by=request.user).order_by('-expense__date_paid')
    
    # (NEW) Get "Settled History"
    settled_history = ExpenseSplit.objects.filter(
        Q(owed_by=request.user) | Q(expense__paid_by=request.user),
        is_settled=True
    ).order_by('-expense__date_paid')

    context = {
        'balance': balance,
        'total_you_paid': total_you_paid, # Pass new value to template
        'form': expense_form,
        'my_debts': my_debts,
        'my_credits': my_credits,
        'settled_history': settled_history, # Pass new list to template
    }
    return render(request, 'dorm/expenses.html', context)


@login_required
@household_required
def grocery_view(request):
    """
    Handles both displaying and adding/removing grocery items.
    """
    profile, household = get_user_household(request)
    
    # --- This is the new logic for handling POST requests ---
    if request.method == 'POST':
        if 'add-item' in request.POST:
            # User is adding a new item
            form = GroceryItemForm(request.POST)
            if form.is_valid():
                item = form.save(commit=False)
                item.household = household
                item.added_by = request.user
                item.save()
                messages.success(request, f"{request.user.profile.display_name} added a New Grocery Item: {item.title}")

                return redirect('grocery') # Redirect to clear the form
        
        elif 'remove-item' in request.POST:
            # User is removing an item
            item_id = request.POST.get('remove-item')
            item = get_object_or_404(GroceryItem, id=item_id, household=household)
            # You could add extra checks here (e.g., only adder can remove)
            item.delete()
            return redirect('grocery')

    # --- This is the GET request logic ---
    form = GroceryItemForm() # Create an empty form
    items = GroceryItem.objects.filter(
        household=household, 
        is_purchased=False
    ).order_by('-created_at')
    
    context = {
        'grocery_items': items,
        'form': form, # Add the form to the context
    }
    return render(request, 'dorm/grocery.html', context)


@login_required
@household_required
def guests_view(request):
    profile, household = get_user_household(request)
    
    # --- ADD THIS FORM LOGIC ---
    if request.method == 'POST' and 'add-guest' in request.POST:
        form = GuestLogForm(request.POST)
        if form.is_valid():
            guest = form.save(commit=False)
            guest.household = household
            guest.hosted_by = request.user
            guest.save()
            messages.success(request, f"{request.user.profile.display_name} has invited a New Guest: {guest.title}")

            return redirect('guests')
    # --- END FORM LOGIC ---
    
    guest_form = GuestLogForm()

    context = {
        'guests': GuestLog.objects.filter(household=household, departure_time__gte=timezone.now()).order_by('arrival_time'),
        'form': guest_form, # <-- ADD THIS
    }
    return render(request, 'dorm/guests.html', context)


@login_required
@household_required
def edit_guest_view(request, pk):
    profile, household = get_user_household(request)
    guest = get_object_or_404(GuestLog, pk=pk, household=household)

    # Security check: Only the host can edit
    if guest.hosted_by != request.user:
        return redirect('guests')

    if request.method == 'POST':
        form = GuestLogForm(request.POST, instance=guest)
        if form.is_valid():
            form.save()
            return redirect('guests')
    else:
        form = GuestLogForm(instance=guest)
    
    return render(request, 'dorm/edit_guest.html', {'form': form, 'guest': guest})


@login_required
@household_required
def announcements_view(request):
    profile, household = get_user_household(request)
    
    # --- (NEW) FORM LOGIC ---
    if request.method == 'POST' and 'add-announcement' in request.POST:
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.household = household
            announcement.posted_by = request.user
            announcement.save()
            messages.success(request, f"{request.user.profile.display_name} added a New Announcement: {announcement.title}")

            return redirect('announcements')
            
    announcement_form = AnnouncementForm()
    # --- END FORM LOGIC ---

    context = {
        'announcements': Announcement.objects.filter(household=household).order_by('-created_at'),
        'form': announcement_form, # <-- Add form to context
    }
    return render(request, 'dorm/announcements.html', context)

# --- ADD THIS NEW VIEW ---
@login_required
def household_management_view(request):
    """
    Handles both creating a new household and joining an existing one.
    """

    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user, household=None)
    
    # If user is already in a household, just send them home
    if profile.household:
        return redirect('home')

    create_form = CreateHouseholdForm(request.POST or None, prefix='create')
    join_form = JoinHouseholdForm(request.POST or None, prefix='join')

    if request.method == 'POST':
        # Check which form was submitted
        if 'create-submit' in request.POST:
            if create_form.is_valid():
                # User is creating a new household
                household = create_form.save()
                profile.household = household
                profile.save()
                return redirect('home')
        
        elif 'join-submit' in request.POST:
            if join_form.is_valid():
                # User is joining a household
                invite_code = join_form.cleaned_data['invite_code']
                household = Household.objects.get(invite_code=invite_code)
                profile.household = household
                profile.save()
                return redirect('home')

    context = {
        'create_form': create_form,
        'join_form': join_form,
    }
    return render(request, 'dorm/household_management.html', context)



# --- (NEW) Settings & Household Views ---

@login_required
def settings_view(request):
    profile = request.user.profile
    household = profile.household
    
    # Household update form
    h_form = UpdateHouseholdForm(request.POST or None, instance=household, prefix='household')
    
    # Profile update form
    p_form = EditProfileForm(request.POST or None, instance=request.user, prefix='profile')

    if request.method == 'POST':
        if 'update-household' in request.POST:
            if h_form.is_valid():
                h_form.save()
                messages.success(request, "Household name updated!")
                return redirect('settings')
        
        if 'update-profile' in request.POST:
            if p_form.is_valid():
                p_form.save()
                messages.success(request, "Profile updated!")
                return redirect('settings')
    
    members = UserProfile.objects.filter(household=household) if household else []

    context = {
        'h_form': h_form,
        'p_form': p_form,
        'members': members,
        # 'household' is already in context from our global processor
    }
    return render(request, 'dorm/settings.html', context)

@login_required
def delete_account_view(request):
    """
    Deletes the user's account.
    """
    if request.method == 'POST':
        user = request.user
        user.delete()
        messages.success(request, "Your account has been deleted.")
        return redirect('login') # Redirect to login page
    
    # If GET, just redirect to settings
    return redirect('settings')


@login_required
def leave_household_view(request):
    """
    Handles the user leaving their household.
    This should only be accessible via POST.
    """
    if request.method == 'POST':
        try:
            profile = request.user.profile
            profile.household = None
            profile.save()
            # Redirect to the page where they can join/create a new one
            return redirect('household_management')
        except UserProfile.DoesNotExist:
            pass # Handle error if profile doesn't exist

    # If GET, just redirect to settings
    return redirect('settings')


# --- (NEW) Announcement Action Views ---

@login_required
@household_required
def edit_announcement_view(request, pk):
    """
    Handles editing an existing announcement.
    'pk' is the primary key (ID) of the announcement.
    """
    profile, household = get_user_household(request)
    announcement = get_object_or_404(Announcement, pk=pk, household=household)

    # Security check: Only the poster can edit
    if announcement.posted_by != request.user:
        return redirect('announcements') # Or show an error

    if request.method == 'POST':
        # Populate the form with the POST data AND the existing instance
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            return redirect('announcements')
    else:
        # On GET, populate the form with the existing announcement data
        form = AnnouncementForm(instance=announcement)
    
    # We'll re-use the base.html modal for this
    context = {'form': form, 'announcement': announcement}
    return render(request, 'dorm/edit_announcement.html', context)


@login_required
@household_required
def delete_announcement_view(request, pk):
    """
    Handles deleting an announcement.
    """
    profile, household = get_user_household(request)
    announcement = get_object_or_404(Announcement, pk=pk, household=household)

    # Security check: Only the poster can delete
    if announcement.posted_by == request.user and request.method == 'POST':
        announcement.delete()
        
    return redirect('announcements')





