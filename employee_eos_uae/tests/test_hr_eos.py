# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from datetime import date


class TestHrEos(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Employee = self.env['hr.employee']
        self.Contract = self.env['hr.contract']
        self.EOS = self.env['hr.end.of.service']

        self.employee = self.Employee.create({
            'name': 'John EOS',
        })
        self.contract = self.Contract.create({
            'name': 'Test Contract',
            'employee_id': self.employee.id,
            'wage': 9000.0,
            'date_start': date(2019, 1, 1),
            'state': 'open',
        })

    def test_federal_gratuity_calculation(self):
        eos = self.EOS.create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'service_start_date': date(2019, 1, 1),
            'service_end_date': date(2024, 1, 1),
            'wage_base': 9000.0,
            'free_zone_rule': 'none',
            'leave_balance_days': 5.0,
        })
        eos._compute_service_years()
        eos._compute_daily_wage()
        eos._compute_amounts()

        # 5 years * 21 days * (9000/30) = 5*21*300 = 31500
        self.assertAlmostEqual(eos.gratuity_amount, 31500.0, places=2)
        self.assertAlmostEqual(eos.leave_payout_amount, 5 * 300.0, places=2)
        self.assertGreater(eos.total_settlement, 0.0)

    def test_dmcc_gratuity_calculation(self):
        eos = self.EOS.create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'service_start_date': date(2019, 1, 1),
            'service_end_date': date(2026, 1, 1),
            'wage_base': 9000.0,
            'free_zone_rule': 'dmcc',
        })
        eos._compute_service_years()
        eos._compute_daily_wage()
        eos._compute_amounts()

        # DMCC simplified uses same brackets; for 7 years expect 5*21 + 2*30 = 165 days * 300 = 49500
        self.assertAlmostEqual(eos.gratuity_amount, 49500.0, places=2)


