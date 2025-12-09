from django import forms
from .models import Household, Expense, Chore, Membership


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ["name", "address", "join_code"]


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        # household and paid_by are set in the view
        fields = ["title", "amount", "category", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }


class ChoreForm(forms.ModelForm):
    """Chore form, household is passed in from the view to limit choices."""

    class Meta:
        model = Chore
        # assigned_to is a Membership
        fields = ["title", "assigned_to", "due_date", "frequency", "status"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        household = kwargs.pop("household", None)
        super().__init__(*args, **kwargs)

        # Limit assigned_to to memberships for this household
        if household is not None:
            self.fields["assigned_to"].queryset = Membership.objects.filter(
                household=household
            )
