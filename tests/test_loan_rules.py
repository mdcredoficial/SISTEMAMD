import unittest
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from loan_rules import (
    calculate_multi_installment_amount,
    compute_loan_snapshot,
    get_next_due_date_after_interest_renegotiation,
)


@dataclass
class FakePayment:
    amount_paid: Decimal
    payment_date: date


@dataclass
class FakeLoan:
    amount: Decimal
    interest_percent: Decimal
    loan_type: str
    loan_date: date
    due_date: date
    term_days: int = 30
    term_weeks: int = 4
    late_fee_amount: Decimal = Decimal('20.00')
    late_fee_interval_days: int = 2
    charge_on_sundays: bool = True
    is_active: bool = True
    payments: list = field(default_factory=list)

    def interest_amount(self):
        return Decimal(self.amount) * Decimal(self.interest_percent) / Decimal('100')


class LoanRulesTestCase(unittest.TestCase):
    def test_diario_27_dias_atraso_gera_13_multas(self):
        loan = FakeLoan(
            amount=Decimal('1000.00'),
            interest_percent=Decimal('20'),
            loan_type='diario',
            loan_date=date(2026, 3, 1),
            due_date=date(2026, 3, 31),
            term_days=30,
            late_fee_amount=Decimal('20.00'),
            late_fee_interval_days=2,
        )
        snap = compute_loan_snapshot(loan, ref_date=date(2026, 3, 29))
        self.assertEqual(snap['days_overdue'], 27)
        self.assertEqual(snap['fine'], Decimal('260.00'))

    def test_semanal_exemplo_20_04_total_740(self):
        loan = FakeLoan(
            amount=Decimal('1000.00'),
            interest_percent=Decimal('20'),
            loan_type='semanal',
            loan_date=date(2026, 3, 30),
            due_date=date(2026, 4, 27),
            term_weeks=4,
            late_fee_amount=Decimal('20.00'),
            late_fee_interval_days=1,
            payments=[FakePayment(amount_paid=Decimal('380.00'), payment_date=date(2026, 4, 10))],
        )
        snap = compute_loan_snapshot(loan, ref_date=date(2026, 4, 20))
        self.assertEqual(snap['fine'], Decimal('140.00'))
        self.assertEqual(snap['current_due_amount'], Decimal('740.00'))

    def test_semanal_multiplas_parcelas_soma_multa_da_atrasada(self):
        loan = FakeLoan(
            amount=Decimal('1000.00'),
            interest_percent=Decimal('20'),
            loan_type='semanal',
            loan_date=date(2026, 3, 30),
            due_date=date(2026, 4, 27),
            term_weeks=4,
            late_fee_amount=Decimal('20.00'),
            late_fee_interval_days=1,
            payments=[FakePayment(amount_paid=Decimal('380.00'), payment_date=date(2026, 4, 10))],
        )
        amount = calculate_multi_installment_amount(loan, 2, ref_date=date(2026, 4, 20))
        self.assertEqual(amount, Decimal('740.00'))


    def test_semanal_multas_sao_somadas_por_parcela_vencida(self):
        loan = FakeLoan(
            amount=Decimal('1000.00'),
            interest_percent=Decimal('20'),
            loan_type='semanal',
            loan_date=date(2026, 3, 25),
            due_date=date(2026, 4, 22),
            term_weeks=4,
            late_fee_amount=Decimal('20.00'),
            late_fee_interval_days=1,
            payments=[],
        )
        snap = compute_loan_snapshot(loan, ref_date=date(2026, 4, 23))
        self.assertEqual(snap['days_overdue'], 22)
        # Parcelas vencidas em 1, 8, 15 e 22/04 acumulam 1 + 8 + 15 + 22 dias.
        self.assertEqual(snap['fine_count'], 46)
        self.assertEqual(snap['fine'], Decimal('920.00'))

    def test_mensal_negociar_juros_mantem_mes_base_original(self):
        loan = FakeLoan(
            amount=Decimal('1000.00'),
            interest_percent=Decimal('20'),
            loan_type='mensal',
            loan_date=date(2026, 3, 28),
            due_date=date(2026, 4, 28),
            late_fee_amount=Decimal('20.00'),
            late_fee_interval_days=1,
        )
        next_due = get_next_due_date_after_interest_renegotiation(loan, payment_date=date(2026, 5, 5))
        self.assertEqual(next_due, date(2026, 5, 28))


if __name__ == '__main__':
    unittest.main()
