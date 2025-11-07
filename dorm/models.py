from django.db import models
from django.conf import settings # Used to link to the built-in User model
import decimal # Used for balance calculations
import uuid

# 1. Household Model (Your "Group" table)
# This is the central group that all roommates belong to.
class Household(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    invite_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    def __str__(self):
        return self.name

# 2. UserProfile Model
# This extends Django's built-in User to link them to a Household.
class UserProfile(models.Model):
    # This creates a one-to-one link with Django's built-in User model
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    
    # Each user belongs to one household.
    household = models.ForeignKey(Household, on_delete=models.SET_NULL, null=True, blank=True, related_name="members")

    def __str__(self):
        return f"{self.user.username}'s Profile"


    @property
    def display_name(self):
        if self.user.first_name:
            return self.user.first_name
        return self.user.username
    

    def get_balance(self):
        total_you_are_owed = decimal.Decimal(0)
        total_you_owe = decimal.Decimal(0)

        # 1. Find all expenses YOU paid for
        for expense in self.user.expenses_paid.all():
            # Find all splits for that expense where others (not you) haven't settled up
            splits = expense.splits.filter(is_settled=False).exclude(owed_by=self.user)
            for split in splits:
                total_you_are_owed += split.amount_owed

        # 2. Find all expense splits YOU owe on
        splits_you_owe = self.user.debts.filter(is_settled=False).exclude(expense__paid_by=self.user)
        for split in splits_you_owe:
            total_you_owe += split.amount_owed

        # Return the net balance
        return total_you_are_owed - total_you_owe

# 3. Chore Model
class Chore(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="chores")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # The user responsible for this chore
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="chores")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="chores_created")
    due_date = models.DateField()
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (Due: {self.due_date})"

# 4. Expense Model
class Expense(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="expenses")
    title = models.CharField(max_length=200)
    # Using DecimalField is best practice for money
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # The user who paid the bill
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expenses_paid")
    date_paid = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (₹{self.amount})"

# 5. ExpenseSplit Model (Your "ExpenseShare" table)
# This tracks who owes what for each expense.
class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="splits")
    
    # The user who owes a share of the bill
    owed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="debts")
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2)
    is_settled = models.BooleanField(default=False) # 'status' in your diagram

    class Meta:
        # Ensures a user can't be listed twice for the same expense
        unique_together = ('expense', 'owed_by')

    def __str__(self):
        return f"{self.owed_by.username} owes ₹{self.amount_owed} for {self.expense.title}"

# 6. GroceryItem Model
class GroceryItem(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="groceries")
    item_name = models.CharField(max_length=100) # 'item_name' from your diagram
    quantity = models.CharField(max_length=50, blank=True, null=True) # e.g., "1L" or "x12"
    
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="groceries_added")
    is_purchased = models.BooleanField(default=False) # 'status' in your diagram
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.item_name

# 7. GuestLog Model (Your "Guest Log" table)
class GuestLog(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="guests")
    guest_name = models.CharField(max_length=100) # 'guestName' from your diagram
    
    # The user who is hosting the guest
    hosted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="guests_hosted")
    arrival_time = models.DateTimeField()
    departure_time = models.DateTimeField()

    def __str__(self):
        return f"{self.guest_name} (Guest of {self.hosted_by.username})"

# 8. Announcement Model
class Announcement(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=200)
    message = models.TextField() # 'message' from your diagram
    
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="announcements_posted")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    


