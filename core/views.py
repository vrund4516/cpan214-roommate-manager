from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import redirect

from .models import Household, Membership, Expense, Chore, ExpenseShare
from .forms import HouseholdForm, ExpenseForm, ChoreForm


def home_redirect(request):
    """If user is logged in go to dashboard, else go to login page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


@login_required
def dashboard(request):
    """Simple dashboard: show households where this user is a member."""
    memberships = Membership.objects.filter(user=request.user)
    households = [m.household for m in memberships]

    context = {
        'households': households,
    }
    # IMPORTANT: template name is EXACTLY 'core/dashboard.html'
    return render(request, 'core/dashboard.html', context)


@login_required
def household_detail(request, pk):
    """Show one household with its expenses, chores, and balances."""
    household = get_object_or_404(Household, pk=pk)

    # Ensure user is a member of this household
    Membership.objects.get(user=request.user, household=household)

    expenses = Expense.objects.filter(household=household).order_by('-date')
    chores = Chore.objects.filter(household=household).order_by('due_date')

    # Balance calculation: how much each member paid vs owes
    memberships = Membership.objects.filter(household=household).select_related('user')
    balances = []
    for m in memberships:
        paid_total = Expense.objects.filter(
            household=household, paid_by=m
        ).aggregate(total=Sum('amount'))['total'] or 0

        share_total = ExpenseShare.objects.filter(
            expense__household=household, member=m
        ).aggregate(total=Sum('share_amount'))['total'] or 0

        balances.append({
            'membership': m,
            'paid_total': paid_total,
            'share_total': share_total,
            'balance': paid_total - share_total,  # positive = others owe them
        })

    context = {
        'household': household,
        'expenses': expenses,
        'chores': chores,
        'balances': balances,
    }
    return render(request, 'core/household_detail.html', context)


@login_required
def household_create(request):
    """Create a new household and make current user the admin member."""
    if request.method == 'POST':
        form = HouseholdForm(request.POST)
        if form.is_valid():
            household = form.save(commit=False)
            household.created_by = request.user
            household.save()

            # Create membership as admin
            Membership.objects.create(
                user=request.user,
                household=household,
                role='admin',
                share_percentage=0
            )

            return redirect('household_detail', pk=household.pk)
    else:
        form = HouseholdForm()

    return render(request, 'core/household_form.html', {'form': form})


@login_required
def expense_create(request, household_pk):
    """Create a new expense for a household and split cost equally."""
    household = get_object_or_404(Household, pk=household_pk)
    membership = get_object_or_404(Membership, user=request.user, household=household)

    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.household = household
            expense.paid_by = membership
            expense.save()

            # Split equally among all members
            members = Membership.objects.filter(household=household)
            count = members.count()
            if count > 0:
                per_head = expense.amount / count
                for m in members:
                    ExpenseShare.objects.create(
                        expense=expense,
                        member=m,
                        share_amount=per_head
                    )

            return redirect('household_detail', pk=household.pk)
    else:
        form = ExpenseForm()

    return render(request, 'core/expense_form.html', {
        'form': form,
        'household': household,
    })


@login_required
def chore_create(request, household_pk):
    """Create a new chore for a household."""
    household = get_object_or_404(Household, pk=household_pk)
    Membership.objects.get(user=request.user, household=household)

    if request.method == 'POST':
        form = ChoreForm(request.POST, household=household)
        if form.is_valid():
            chore = form.save(commit=False)
            chore.household = household
            chore.save()
            return redirect('household_detail', pk=household.pk)
    else:
        form = ChoreForm(household=household)

    return render(request, 'core/chore_form.html', {
        'form': form,
        'household': household,
    })


@login_required
def chore_toggle_status(request, pk):
    """Mark a chore as completed / pending."""
    chore = get_object_or_404(Chore, pk=pk)
    # Only members of the household may do this
    Membership.objects.get(user=request.user, household=chore.household)

    if chore.status == 'pending':
        chore.status = 'completed'
    else:
        chore.status = 'pending'
    chore.save()

    return redirect('household_detail', pk=chore.household.pk)


@login_required
def logout_view(request):
    """Log out and go back to login page."""
    logout(request)
    return redirect('login')



@login_required
def profile_redirect(request):
    """Handle /accounts/profile/ by sending the user to the dashboard."""
    return redirect('dashboard')
