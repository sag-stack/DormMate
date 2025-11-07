from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    UserProfile, Household, GroceryItem, Chore, Expense, GuestLog, Announcement
)
import uuid

# --- Custom Widgets ---
class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'

class DateInput(forms.DateInput):
    input_type = 'date'

# --- Auth Forms (Unchanged) ---
class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            UserProfile.objects.create(user=user, household=None)
        return user

class CreateHouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ['name']

class JoinHouseholdForm(forms.Form):
    invite_code = forms.CharField(label="Invite Code", max_length=50)

    def clean_invite_code(self):
        code = self.cleaned_data['invite_code']
        try:
            uuid_code = uuid.UUID(code)
            if not Household.objects.filter(invite_code=uuid_code).exists():
                raise forms.ValidationError("Invalid invite code.")
        except ValueError:
            raise forms.ValidationError("Invalid format.")
        return uuid_code

# --- Module Forms (Updated) ---

class GroceryItemForm(forms.ModelForm):
    class Meta:
        model = GroceryItem
        fields = ['item_name', 'quantity']
        # ... widgets (unchanged) ...

class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ['title', 'description', 'assigned_to', 'due_date']
        widgets = {
            'due_date': DateInput(),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        household = kwargs.pop('household', None)
        super().__init__(*args, **kwargs)
        if household:
            self.fields['assigned_to'].queryset = User.objects.filter(
                profile__household=household
            )

class ExpenseForm(forms.ModelForm):
    """
    -- THIS FORM IS NOW UPGRADED --
    It now includes a 'split_with' field to select users.
    """
    split_with = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(), # We set this in __init__
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Split with"
    )

    class Meta:
        model = Expense
        fields = ['title', 'amount', 'split_with']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Pizza Night'}),
            'amount': forms.NumberInput(attrs={'placeholder': 'e.g., 900.00'}),
        }

    def __init__(self, *args, **kwargs):
        household = kwargs.pop('household', None)
        super().__init__(*args, **kwargs)
        if household:
            # Get all users in the household
            members = User.objects.filter(profile__household=household)
            
            # Set the queryset for the 'split_with' field
            self.fields['split_with'].queryset = members
            
            # Set all members to be checked by default for convenience
            self.fields['split_with'].initial = members

class GuestLogForm(forms.ModelForm):
    class Meta:
        model = GuestLog
        # ... fields and widgets (unchanged) ...
        fields = ['guest_name', 'arrival_time', 'departure_time']
        widgets = {
            'arrival_time': DateTimeInput(),
            'departure_time': DateTimeInput(),
        }

# --- (NEW) Announcement Form ---
class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'message']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Water Supply Cutoff'}),
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Maintenance work on Sept 15...'}),
        }


class UpdateHouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ['name']
        labels = {
            'name': 'Household Name'
        }

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User # We are editing the built-in User
        fields = ['first_name', 'last_name', 'email']