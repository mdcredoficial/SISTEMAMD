from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable

from dateutil.relativedelta import relativedelta

PROTECTED_LOAN_RULES_VERSION = "2026-03-28-rules-freeze-v1"
ZERO = Decimal('0.00')


def quantize_money(value: Any) -> Decimal:
    return Decimal(value or 0).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def month_add(dt: date) -> date:
    return dt + relativedelta(months=1)


def loan_cycle_label(loan: Any) -> str:
    loan_type = getattr(loan, 'loan_type', 'mensal') or 'mensal'
    if loan_type == 'diario':
        return 'Diário'
    if loan_type == 'semanal':
        return 'Semanal'
    return 'Mensal'


def installment_count_for_default(loan: Any) -> int:
    loan_type = getattr(loan, 'loan_type', 'mensal') or 'mensal'
    if loan_type == 'diario':
        return max(int(getattr(loan, 'term_days', 30) or 30), 1)
    if loan_type == 'semanal':
        return max(int(getattr(loan, 'term_weeks', 4) or 4), 1)
    return 1


def daily_due_dates(start_date: date, installments: int, charge_on_sundays: bool = True) -> list[date]:
    due_dates: list[date] = []
    cursor = start_date
    while len(due_dates) < max(int(installments or 0), 0):
        cursor = cursor + relativedelta(days=1)
        if not charge_on_sundays and cursor.weekday() == 6:
            continue
        due_dates.append(cursor)
    return due_dates


def paid_installments_count(total_paid: Any, installment_amount: Any, total_installments: int) -> int:
    installment_amount = Decimal(installment_amount or 0)
    if installment_amount <= 0:
        return 0
    total_paid = Decimal(total_paid or 0)
    count = int(total_paid // installment_amount)
    return max(0, min(count, int(total_installments or 0)))


def _base_schedule(loan: Any) -> tuple[Decimal, int, list[date], Decimal, Decimal, Decimal, str]:
    interest = quantize_money(loan.interest_amount())
    principal = quantize_money(Decimal(getattr(loan, 'amount', 0) or 0))
    total_contract = quantize_money(principal + interest)
    loan_type = getattr(loan, 'loan_type', 'mensal') or 'mensal'
    charge_on_sundays = bool(getattr(loan, 'charge_on_sundays', True))
    if loan_type == 'diario':
        total_installments = max(int(getattr(loan, 'term_days', 30) or 30), 1)
        installment_amount = quantize_money(total_contract / total_installments)
        due_dates = daily_due_dates(loan.loan_date, total_installments, charge_on_sundays)
    elif loan_type == 'semanal':
        total_installments = max(int(getattr(loan, 'term_weeks', 4) or 4), 1)
        installment_amount = quantize_money(total_contract / total_installments)
        due_dates = [loan.loan_date + relativedelta(weeks=i) for i in range(1, total_installments + 1)]
    else:
        total_installments = 1
        installment_amount = total_contract
        due_dates = [loan.due_date]
    return installment_amount, total_installments, due_dates, interest, principal, total_contract, loan_type


def _sorted_payments(loan: Any) -> list[Any]:
    return sorted(
        list(getattr(loan, 'payments', []) or []),
        key=lambda p: (getattr(p, 'payment_date', date.min), getattr(p, 'id', 0)),
    )


def _build_open_installments(due_dates: list[date], installment_amount: Decimal, principal_paid: Decimal, ref_date: date) -> list[dict[str, Any]]:
    installments = []
    paid_left = Decimal(principal_paid or 0)
    for index, due_on in enumerate(due_dates, start=1):
        installment = Decimal(installment_amount)
        covered = min(paid_left, installment)
        unpaid = quantize_money(installment - covered)
        paid_left = quantize_money(paid_left - covered)
        is_due_today = ref_date == due_on
        is_overdue = ref_date > due_on and unpaid > 0
        days_overdue = (ref_date - due_on).days if is_overdue else 0
        installments.append({
            'number': index,
            'due_date': due_on,
            'amount': quantize_money(installment),
            'unpaid': unpaid,
            'is_due_today': is_due_today and unpaid > 0,
            'is_overdue': is_overdue,
            'days_overdue': days_overdue,
            'is_upcoming': ref_date < due_on and unpaid > 0,
        })
    return installments


def _daily_fine_count(days_overdue: int, interval_days: int) -> int:
    interval_days = max(int(interval_days or 1), 1)
    return max(int(days_overdue or 0), 0) // interval_days


def _fine_breakdown_for_open_installments(loan: Any, installments: list[dict[str, Any]]) -> tuple[int, Decimal, list[dict[str, Any]]]:
    loan_type = getattr(loan, 'loan_type', 'mensal') or 'mensal'
    late_fee_amount = quantize_money(getattr(loan, 'late_fee_amount', Decimal('20')) or 0)
    late_fee_interval_days = max(int(getattr(loan, 'late_fee_interval_days', 1) or 1), 1)
    overdue_items = [item for item in installments if item['is_overdue']]
    if not overdue_items:
        return 0, ZERO, []

    details: list[dict[str, Any]] = []
    if loan_type == 'diario':
        max_days_overdue = max(item['days_overdue'] for item in overdue_items)
        fine_count = _daily_fine_count(max_days_overdue, late_fee_interval_days)
        fine_total = quantize_money(late_fee_amount * fine_count)
        return fine_count, fine_total, []

    if loan_type == 'semanal':
        total_count = 0
        total_fine = ZERO
        for item in overdue_items:
            fine_count = max(int(item['days_overdue'] or 0), 0)
            fine_value = quantize_money(late_fee_amount * fine_count)
            total_count += fine_count
            total_fine += fine_value
            details.append({
                'number': item['number'],
                'due_date': item['due_date'],
                'days_overdue': item['days_overdue'],
                'fine_count': fine_count,
                'fine_amount': fine_value,
                'installment_amount': quantize_money(item['unpaid']),
                'total_amount': quantize_money(item['unpaid'] + fine_value),
            })
        return total_count, quantize_money(total_fine), details

    fine_count = max(item['days_overdue'] for item in overdue_items)
    fine_total = quantize_money(late_fee_amount * fine_count)
    return fine_count, fine_total, []


def _fine_for_open_installments(loan: Any, installments: list[dict[str, Any]]) -> Decimal:
    _, fine_total, _ = _fine_breakdown_for_open_installments(loan, installments)
    return fine_total


def principal_paid_for_schedule(loan: Any) -> Decimal:
    _, total_installments, due_dates, _, _, _, loan_type = _base_schedule(loan)
    if loan_type not in ('diario', 'semanal'):
        return quantize_money(sum(Decimal(getattr(p, 'amount_paid', 0) or 0) for p in _sorted_payments(loan)))

    installment_amount, _, due_dates, _, _, _, _ = _base_schedule(loan)
    principal_paid = ZERO
    max_principal = quantize_money(installment_amount * total_installments)

    for payment in _sorted_payments(loan):
        payment_amount = quantize_money(getattr(payment, 'amount_paid', 0) or 0)
        payment_date = getattr(payment, 'payment_date', date.today())
        open_installments = _build_open_installments(due_dates, installment_amount, principal_paid, payment_date)
        fine_due = _fine_for_open_installments(loan, open_installments)
        principal_component = max(payment_amount - fine_due, ZERO)
        principal_paid = quantize_money(min(max_principal, principal_paid + principal_component))

    return principal_paid


def build_installment_schedule(loan: Any, ref_date: date | None = None) -> dict[str, Any]:
    ref_date = ref_date or date.today()
    total_paid = principal_paid_for_schedule(loan)
    installment_amount, total_installments, due_dates, interest, principal, total_contract, loan_type = _base_schedule(loan)

    installments = _build_open_installments(due_dates, installment_amount, total_paid, ref_date)
    return {
        'loan_type': loan_type,
        'total_paid': quantize_money(total_paid),
        'interest_amount': interest,
        'principal': principal,
        'total_contract': total_contract,
        'installment_amount': quantize_money(installment_amount),
        'total_installments': total_installments,
        'installments': installments,
    }


def calculate_multi_installment_amount(loan: Any, quantity: int, ref_date: date | None = None) -> Decimal:
    ref_date = ref_date or date.today()
    quantity = max(int(quantity or 1), 1)
    schedule = build_installment_schedule(loan, ref_date=ref_date)
    loan_type = schedule['loan_type']
    late_fee_amount = quantize_money(getattr(loan, 'late_fee_amount', Decimal('20')) or 0)
    late_fee_interval_days = max(int(getattr(loan, 'late_fee_interval_days', 1) or 1), 1)

    if loan_type not in ('diario', 'semanal'):
        return quantize_money(schedule['total_contract'])

    pending = [i for i in schedule['installments'] if i['unpaid'] > 0]
    selected = pending[:quantity]
    amount = sum((Decimal(item['unpaid']) for item in selected), ZERO)

    overdue_items = [item for item in selected if item['is_overdue']]
    if overdue_items:
        if loan_type == 'diario':
            max_days_overdue = max(item['days_overdue'] for item in overdue_items)
            fines = _daily_fine_count(max_days_overdue, late_fee_interval_days)
            amount += late_fee_amount * fines
        elif loan_type == 'semanal':
            for item in overdue_items:
                amount += late_fee_amount * max(int(item['days_overdue'] or 0), 0)
        else:
            fines = max(item['days_overdue'] for item in overdue_items)
            amount += late_fee_amount * fines

    return quantize_money(amount)


def compute_loan_snapshot(loan: Any, ref_date: date | None = None, installment_count_for: Callable[[Any], int] | None = None) -> dict[str, Any]:
    ref_date = ref_date or date.today()
    installment_count_for = installment_count_for or installment_count_for_default
    total_paid = principal_paid_for_schedule(loan)
    installment_amount, total_installments, due_dates, interest, principal, total_contract, loan_type = _base_schedule(loan)
    late_fee_amount = quantize_money(getattr(loan, 'late_fee_amount', Decimal('20')) or 0)
    late_fee_interval_days = max(int(getattr(loan, 'late_fee_interval_days', 1) or 1), 1)

    if not getattr(loan, 'is_active', True):
        installments_count = installment_count_for(loan)
        installment_value = quantize_money(total_contract / installments_count) if installments_count else ZERO
        return {
            'loan_type_label': loan_cycle_label(loan),
            'status_label': 'Quitado',
            'days_overdue': 0,
            'fine': ZERO,
            'fine_count': 0,
            'interest_amount': interest,
            'updated_amount': ZERO,
            'settlement_amount': ZERO,
            'renewal_amount': ZERO,
            'total_contract_amount': total_contract,
            'installment_amount': installment_value,
            'paid_amount': total_paid,
            'remaining_amount': ZERO,
            'term_label': loan_cycle_label(loan),
            'schedule_due_amount': ZERO,
            'overdue_installments': 0,
            'current_due_amount': ZERO,
            'overdue_amount': ZERO,
            'next_due_date': None,
            'paid_installments': installments_count,
            'total_installments': installments_count,
            'selected_multi_amount': ZERO,
            'overdue_detail_lines': [],
        }

    if loan_type in ('diario', 'semanal'):
        installments = _build_open_installments(due_dates, installment_amount, total_paid, ref_date)
        remaining = quantize_money(max(total_contract - total_paid, ZERO))

        overdue_installments = 0
        overdue_amount = ZERO
        current_due_amount = ZERO
        scheduled_due_amount = ZERO
        max_days_overdue = 0
        next_due_date = None
        overdue_items = []

        for item in installments:
            if ref_date >= item['due_date']:
                scheduled_due_amount += item['amount']
            if item['is_due_today']:
                current_due_amount += item['unpaid']
                if next_due_date is None:
                    next_due_date = item['due_date']
            elif item['is_overdue']:
                overdue_items.append(item)
                overdue_installments += 1
                overdue_amount += item['unpaid']
                max_days_overdue = max(max_days_overdue, item['days_overdue'])
            elif item['is_upcoming'] and next_due_date is None:
                next_due_date = item['due_date']

        overdue_detail_lines = []
        if loan_type == 'diario':
            fine_count = _daily_fine_count(max_days_overdue, late_fee_interval_days)
            fine_total = quantize_money(late_fee_amount * fine_count)
        else:
            fine_count, fine_total, overdue_detail_lines = _fine_breakdown_for_open_installments(loan, installments)

        scheduled_due_amount = quantize_money(scheduled_due_amount)
        overdue_amount = quantize_money(overdue_amount)
        current_due_amount = quantize_money(current_due_amount)

        if overdue_installments > 0:
            status = 'Atrasado'
        elif current_due_amount > 0:
            status = 'Pagar hoje'
        else:
            status = 'Em dia'

        updated = quantize_money(remaining + fine_total)
        due_now = quantize_money(current_due_amount + overdue_amount + fine_total)
        multiple_amount = calculate_multi_installment_amount(loan, 2, ref_date=ref_date)
        term_label = f"{total_installments} {'dias' if loan_type == 'diario' else 'semanas'}"
        return {
            'loan_type_label': 'Diário' if loan_type == 'diario' else 'Semanal',
            'status_label': status,
            'days_overdue': max_days_overdue,
            'fine': fine_total,
            'fine_count': fine_count,
            'interest_amount': interest,
            'updated_amount': updated,
            'settlement_amount': updated,
            'renewal_amount': due_now,
            'total_contract_amount': total_contract,
            'installment_amount': installment_amount,
            'paid_amount': total_paid,
            'remaining_amount': remaining,
            'term_label': term_label,
            'schedule_due_amount': scheduled_due_amount,
            'overdue_installments': overdue_installments,
            'current_due_amount': due_now,
            'overdue_amount': overdue_amount,
            'next_due_date': next_due_date,
            'paid_installments': paid_installments_count(total_paid, installment_amount, total_installments),
            'total_installments': total_installments,
            'selected_multi_amount': multiple_amount,
            'overdue_detail_lines': overdue_detail_lines,
        }

    if ref_date < loan.due_date:
        status = 'Em dia'
        days_overdue = 0
    elif ref_date == loan.due_date:
        status = 'Pagar hoje'
        days_overdue = 0
    else:
        status = 'Atrasado'
        days_overdue = (ref_date - loan.due_date).days

    fine_count = days_overdue
    fine = quantize_money(fine_count * late_fee_amount)
    updated = quantize_money(total_contract + fine)
    renewal = quantize_money(interest + fine)
    remaining = quantize_money(max(total_contract - total_paid, ZERO))
    due_now = quantize_money((remaining if status != 'Em dia' else ZERO) + fine)
    return {
        'loan_type_label': 'Mensal',
        'status_label': status,
        'days_overdue': days_overdue,
        'fine': fine,
        'fine_count': fine_count,
        'interest_amount': interest,
        'updated_amount': updated,
        'settlement_amount': updated,
        'renewal_amount': renewal,
        'total_contract_amount': total_contract,
        'installment_amount': total_contract,
        'paid_amount': total_paid,
        'remaining_amount': remaining,
        'term_label': '1 mês',
        'schedule_due_amount': total_contract,
        'overdue_installments': 1 if days_overdue > 0 else 0,
        'current_due_amount': due_now,
        'overdue_amount': remaining if days_overdue > 0 else ZERO,
        'next_due_date': loan.due_date,
        'paid_installments': 0 if remaining > 0 else 1,
        'total_installments': 1,
        'selected_multi_amount': ZERO,
        'overdue_detail_lines': [],
    }


def get_next_due_date_after_interest_renegotiation(loan: Any, payment_date: date | None = None) -> date:
    payment_date = payment_date or date.today()
    loan_type = getattr(loan, 'loan_type', 'mensal') or 'mensal'
    if loan_type == 'diario':
        schedule = build_installment_schedule(loan, ref_date=payment_date)
        pending = [item for item in schedule['installments'] if item['unpaid'] > 0 and item['due_date'] > payment_date]
        return pending[0]['due_date'] if pending else payment_date + relativedelta(days=1)
    if loan_type == 'semanal':
        schedule = build_installment_schedule(loan, ref_date=payment_date)
        pending = [item for item in schedule['installments'] if item['unpaid'] > 0 and item['due_date'] > payment_date]
        return pending[0]['due_date'] if pending else payment_date + relativedelta(weeks=1)
    next_due = getattr(loan, 'due_date')
    while next_due <= payment_date:
        next_due = month_add(next_due)
    return next_due
