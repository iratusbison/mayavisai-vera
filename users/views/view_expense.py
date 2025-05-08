
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal
from users.models.expense import ESection, Expense
from users.forms import ESectionForm, ExpenseForm
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from io import BytesIO
from reportlab.lib.styles import getSampleStyleSheet

@login_required
def esection_list(request):
    user_profile = request.user.userprofile
    esections = ESection.objects.filter(user_profile=user_profile)
    total_expenses = Expense.objects.filter(user_profile=user_profile).aggregate(total=Sum('amount'))['total']
    total_expenses = total_expenses or Decimal('0')  # Convert to Decimal
    total_income = request.session.get('total_income',0)
    # Convert to float for session storage
    total_expenses_float = float(total_expenses)
    # Convert total_income and total_expenses to floats
    total_income = float(total_income)
    total_expenses = float(total_expenses)

   # Perform the subtraction
    income_pool = total_income - total_expenses

    # Store the value in the session
    request.session['total_expenses'] = total_expenses_float


    if request.method == 'POST' and 'delete_esection' in request.POST:
        esection_id = request.POST['delete_esection']
        esection = ESection.objects.get(pk=esection_id, user_profile=user_profile)
        esection.delete()
        return redirect('esection_list')

    return render(request, 'esection_list.html', {'esections': esections, 'total_expenses': total_expenses, 'income_pool':income_pool})

@login_required
def add_esection(request):
    user_profile = request.user.userprofile
    if request.method == 'POST':
        form = ESectionForm(request.POST)
        if form.is_valid():
            esection = form.save(commit=False)
            esection.user_profile = user_profile
            esection.save()
            return redirect('esection_list')
    else:
        form = ESectionForm()

    return render(request, 'add_esection.html', {'form': form})

@login_required
def expense_list(request, esection_id):
    user_profile = request.user.userprofile
    esection = get_object_or_404(ESection, pk=esection_id, user_profile=user_profile)
    expenses = Expense.objects.filter(esection=esection, user_profile=user_profile)
    total_expenses = expenses.aggregate(total=Sum('amount'))['total']
    total_expenses = total_expenses or Decimal('0')

    return render(request, 'expense_list.html', {'expenses': expenses, 'total_expenses': total_expenses, 'esection': esection})

@login_required
def add_expense(request, esection_id):
    user_profile = request.user.userprofile
    esection = get_object_or_404(ESection, pk=esection_id, user_profile=user_profile)
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.esection = esection
            expense.user_profile = user_profile
            expense.save()
            return redirect('expense_list', esection_id=esection_id)
    else:
        form = ExpenseForm()

    expenses = Expense.objects.filter(esection=esection, user_profile=user_profile)
    total_expense = sum(expense.amount for expense in expenses)

    return render(request, 'add_expense.html', {'esection': esection, 'form': form, 'expenses': expenses, 'total_expense': total_expense})

@login_required
def delete_expense(request, expense_id):
    user_profile = request.user.userprofile
    expense = get_object_or_404(Expense, pk=expense_id, user_profile=user_profile)
    esection_id = expense.esection.id
    if request.method == 'POST':
        expense.delete()
        return redirect('expense_list', esection_id=esection_id)
    return render(request, 'delete_expense.html', {'expense': expense, 'esection_id': esection_id})



@login_required
def generate_pdf(request, esection_id):
    user_profile = request.user.userprofile
    esection = get_object_or_404(ESection, pk=esection_id, user_profile=user_profile)
    expenses = Expense.objects.filter(esection=esection, user_profile=user_profile)

    # Calculate the total expense
    total_expense = sum(expense.amount for expense in expenses)

    # Create an in-memory PDF file
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Add a line with the total expense
    styles = getSampleStyleSheet()
    total_expense_text = Paragraph(f'<b>Total Expense:</b> Rs {total_expense}', styles['Normal'])
    elements.append(total_expense_text)

    # Create a data list for the table
    data = [["Date", "Description", "Amount"]]  # Header row
    for expense in expenses:
        data.append([expense.date, expense.description, f'Rs {expense.amount}'])

    # Define a custom table style
    custom_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    # Create the table with the custom style
    table = Table(data)
    table.setStyle(custom_table_style)

    # Add the table to the elements
    elements.append(table)

    # Build the PDF document
    doc.build(elements)

    # Reset the buffer's position to the start
    buffer.seek(0)

    # Create a Django HttpResponse with the PDF file
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="expense_list_{esection_id}.pdf"'

    # Close the buffer
    buffer.close()

    return response