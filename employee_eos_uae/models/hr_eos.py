# -*- coding: utf-8 -*-

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEndOfService(models.Model):
    _name = 'hr.end.of.service'
    _description = 'End of Service Settlement (UAE)'
    _order = 'settlement_date desc, employee_id'

    name = fields.Char(string='Reference', required=True, copy=False, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', domain="[('employee_id','=',employee_id)]", required=True)

    service_start_date = fields.Date(string='Service Start Date', required=True)
    service_end_date = fields.Date(string='Service End Date', required=True, default=lambda self: date.today())
    settlement_date = fields.Date(string='Settlement Date', required=True, default=lambda self: date.today())

    wage_base = fields.Float(string='Monthly Basic Salary', help='Basic salary used for gratuity calculation')
    daily_wage = fields.Monetary(string='Daily Wage', currency_field='currency_id', compute='_compute_daily_wage', store=True)

    years_of_service = fields.Float(string='Years of Service', compute='_compute_service_years', store=True)

    gratuity_amount = fields.Monetary(string='Gratuity', currency_field='currency_id', compute='_compute_amounts', store=True)
    leave_payout_amount = fields.Monetary(string='Unused Leave Payout', currency_field='currency_id', compute='_compute_amounts', store=True)
    other_payments = fields.Monetary(string='Other Payments', currency_field='currency_id', help='Bonuses, commissions, or other allowances to include')
    deductions = fields.Monetary(string='Deductions', currency_field='currency_id')
    total_settlement = fields.Monetary(string='Total Settlement', currency_field='currency_id', compute='_compute_amounts', store=True)

    free_zone_rule = fields.Selection([
        ('none', 'Federal UAE Labor Law'),
        ('dmcc', 'DMCC Free Zone'),
        ('custom1', 'Custom Rule 1'),
    ], string='Free Zone Rule', default='none', help='Select to apply specific free zone gratuity rules')

    leave_balance_days = fields.Float(string='Unused Leave Days', help='Remaining annual leave days to be paid out')
    annual_leave_days_per_year = fields.Float(string='Annual Leave Days/Year', default=30.0)

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)

    note = fields.Text(string='Details Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.constrains('service_start_date', 'service_end_date')
    def _check_dates(self):
        for record in self:
            if record.service_end_date and record.service_start_date and record.service_end_date < record.service_start_date:
                raise ValidationError(_('Service End Date must be after Start Date.'))

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            self.contract_id = self.employee_id.contract_id
            if self.employee_id.contract_id:
                self.service_start_date = self.employee_id.contract_id.date_start
                # wage base defaults from contract
                self.wage_base = self.employee_id.contract_id.wage

    @api.depends('wage_base')
    def _compute_daily_wage(self):
        for record in self:
            # UAE convention: divide monthly by 30 to get daily wage
            record.daily_wage = (record.wage_base or 0.0) / 30.0

    @api.depends('service_start_date', 'service_end_date')
    def _compute_service_years(self):
        for record in self:
            if record.service_start_date and record.service_end_date:
                delta = relativedelta(record.service_end_date, record.service_start_date)
                # convert to fractional years
                record.years_of_service = (delta.years or 0) + (delta.months or 0) / 12.0 + (delta.days or 0) / 365.0
            else:
                record.years_of_service = 0.0

    def _compute_gratuity_federal(self, years_of_service: float, daily_wage: float) -> float:
        """Federal UAE Labor Law gratuity for permanent employees.
        - 21 days per year for first 5 years
        - 30 days per year thereafter
        - cap at 2 years of wage (i.e., 24 months)
        """
        if years_of_service <= 0 or daily_wage <= 0:
            return 0.0

        first_segment_years = min(years_of_service, 5.0)
        remaining_years = max(years_of_service - 5.0, 0.0)

        gratuity_days = first_segment_years * 21.0 + remaining_years * 30.0
        gratuity_amount = gratuity_days * daily_wage

        # cap at 24 months of basic wage
        cap_amount = (self.wage_base or 0.0) * 24.0
        return min(gratuity_amount, cap_amount)

    def _compute_gratuity_dmcc(self, years_of_service: float, daily_wage: float) -> float:
        """Example DMCC approach: same brackets but using DMCC specific rounding.
        This is a simplified placeholder compliant approach and can be adjusted.
        - 21 days for first 5 years, 30 days thereafter
        - Rounding up partial years to nearest month then to days basis
        - Same 24 months cap
        """
        if years_of_service <= 0 or daily_wage <= 0:
            return 0.0

        # Convert fractional years to months rounded up to nearest month
        total_months = int(round(years_of_service * 12.0))
        first_segment_months = min(total_months, 60)
        remaining_months = max(total_months - 60, 0)

        gratuity_days = (first_segment_months / 12.0) * 21.0 + (remaining_months / 12.0) * 30.0
        gratuity_amount = gratuity_days * daily_wage

        cap_amount = (self.wage_base or 0.0) * 24.0
        return min(gratuity_amount, cap_amount)

    def _compute_gratuity_by_rule(self, years_of_service: float, daily_wage: float) -> float:
        self.ensure_one()
        if self.free_zone_rule == 'dmcc':
            return self._compute_gratuity_dmcc(years_of_service, daily_wage)
        elif self.free_zone_rule == 'custom1':
            # Placeholder custom: 20 days for first 3 years, 30 days thereafter. Still cap at 24 months.
            if years_of_service <= 0 or daily_wage <= 0:
                return 0.0
            first = min(years_of_service, 3.0)
            rest = max(years_of_service - 3.0, 0.0)
            days = first * 20.0 + rest * 30.0
            amount = days * daily_wage
            cap_amount = (self.wage_base or 0.0) * 24.0
            return min(amount, cap_amount)
        else:
            return self._compute_gratuity_federal(years_of_service, daily_wage)

    def _compute_leave_payout(self, unused_days: float, daily_wage: float) -> float:
        if unused_days <= 0 or daily_wage <= 0:
            return 0.0
        return unused_days * daily_wage

    @api.depends(
        'years_of_service', 'daily_wage', 'leave_balance_days', 'other_payments', 'deductions', 'wage_base', 'free_zone_rule'
    )
    def _compute_amounts(self):
        for record in self:
            gratuity = record._compute_gratuity_by_rule(record.years_of_service, record.daily_wage)
            leave_payout = record._compute_leave_payout(record.leave_balance_days, record.daily_wage)
            total = gratuity + leave_payout + (record.other_payments or 0.0) - (record.deductions or 0.0)
            record.gratuity_amount = gratuity
            record.leave_payout_amount = leave_payout
            record.total_settlement = total

    def action_confirm(self):
        for record in self:
            record.name = amount
            
            if record.name == _('New'):
                record.name = self.env['ir.sequence'].next_by_code('hr.end.of.service') or _('New')
            record.state = 'confirmed'

    def action_done(self):
        rec_with_codes = defaultdict(dict)
        for record in self:
            record.state = 'done'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'




