# -*- coding: utf-8 -*-

import tempfile
import os
import re

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

from .namedtuples import *
from .qdriver import QDriver


class EcrRegisterQuorion(models.Model):
    _name = 'ecr.register.quorion'
    _description = 'Quorion Cash Register'
    _inherits = {'ecr.register': 'register_id'}
    _sql_constraints = [
        (
            'check_plu_caption_size', 
            'CHECK((plu_caption_size>0) AND (plu_caption_size<=25))', 
            'PLU caption size must be positive and less than or equal to 25.'
        ),
        (
            'check_department_caption_size', 
            'CHECK((department_caption_size>0) AND (department_caption_size<=25))', 
            'Department caption size must be positive and less than or equal to 25.'
        ),
    ]

    number_of_plu = fields.Integer(required=True, default=1000)
    number_of_departments = fields.Integer(required=True, default=25)
    plu_caption_size = fields.Integer(required=True, default=25)
    department_caption_size = fields.Integer(required=True, default=25)
    illegal_caption_characters = fields.Char(required=True, default=';"')
    illegal_caption_characters_replacement = fields.Char(default=' ')
    sales_report_X = fields.Char(required=True, default='RSX0000004')
    income_report_X = fields.Char(required=True, default='RSX0000006')

    tmp_filename = fields.Char(compute="_compute_tmp_filename")

    register_id = fields.Many2one('ecr.register', required=True, ondelete='cascade')

    @api.model
    def create(self, vals_list):
        vals_list['ecr_model_id'] = self.env.ref('ecr_quorion.ecr_quorion_model').id   
        return super().create(vals_list)

    def copy(self, default=None):
        default = dict(default or {})
        copied_count = self.search_count([('name', '=like', u"Copy of {}%".format(self.name))])
        if not copied_count:
            new_name = u"Copy of {}".format(self.name)
        else:
            new_name = u"Copy of {} ({})".format(self.name, copied_count)
        default['name'] = new_name
        return super(EcrRegisterQuorion, self).copy(default)

    @api.constrains('department_ids')
    def _check_department_ids(self):
        for record in self:
            for dept in record.department_ids:
                if not (dept.code > 0 and dept.code <= record.number_of_departments):
                    raise ValidationError('Department code must be strictly positive and less than or equal to the number of departments.')
    
    @api.constrains('sales_report_X')
    def _check_sales_report_X(self):
        for record in self:
            if not (re.match(r"^R[Ss][Xx][0-9]{7}$", record.sales_report_X) or re.match(r"^R[Uu][Xx][0-9]{9}$", record.sales_report_X)):
                raise UserError('Sales report value is invalid.')

    @api.constrains('income_report_X')
    def _check_income_report_X(self):
        for record in self:
            if not (re.match(r"^R[Ss][Xx][0-9]{7}$", record.income_report_X) or re.match(r"^R[Uu][Xx][0-9]{9}$", record.income_report_X)):
                raise UserError('Income report value is invalid.')

    @api.depends('register_id')
    def _compute_tmp_filename(self):
        for record in self:
            record.tmp_filename = os.path.join(tempfile._get_default_tempdir(), f'register-{self.id}')

    def _write_plu_line(self, file, code:str, caption:str, price:float, department:int):
        file.write(f'10000;{code};"{self.register_id.fix_caption(caption, self.plu_caption_size, self.illegal_caption_characters)}";;{department};;;{self.register_id.price2str(price)};\n')

    def _get_sales_report(self, clear=False):
        cmd = f'NEWFILE={self.tmp_filename}\n'
        report = self.sales_report_X
        if clear:
            report = report.replace('X', 'Z').replace('x', 'z')
        cmd += f'COMMAND={report}'
        with QDriver(self.ip_address, self.port) as q: q.run(cmd)
        report = []
        with open(self.tmp_filename, 'r') as file:
            for line in file:
                datos = line.split(';')
                if len(datos) >=  5 and datos[0] == '1' and datos[1] == '1' and datos[2] == '1' and datos[3] == '4' and datos[4] != '':
                    report.append(SalesReport(datos[4], float(datos[7])))
        return report

    def _get_income_report(self, clear=False):
        cmd = f'NEWFILE={self.tmp_filename}\n'
        report = self.income_report_X
        if clear:
            report = report.replace('X', 'Z').replace('x', 'z')
        cmd += f'COMMAND={report}'
        with QDriver(self.ip_address, self.port) as q: q.run(cmd)
        report = []
        with open(self.tmp_filename, 'r') as file:
            for line in file:
                datos = line.split(';')
                if len(datos) >=  5 and datos[0] == '1' and (datos[1] in {'1', '2'}) and (datos[3] in {'6', '7'}) and datos[4] != '':
                    report.append(IncomeReport(int(datos[4]), float(datos[8])))
        return report

    def _clear_sales_report(self):
        cmd = f'NEWFILE={self.tmp_filename}\n'
        report = self.sales_report_X.replace('X', 'C').replace('x', 'c')
        cmd += f'COMMAND={report}'
        with QDriver(self.ip_address, self.port) as q: q.run(cmd)

    def _clear_income_report(self):
        cmd = f'NEWFILE={self.tmp_filename}\n'
        report = self.income_report_X.replace('X', 'C').replace('x', 'c')
        cmd += f'COMMAND={report}'
        with QDriver(self.ip_address, self.port) as q: q.run(cmd)

    def _write_department_line(self, file, code: int, caption: str):
        file.write(f'5000;{code};"{self.register_id.fix_caption(caption, self.department_caption_size, self.illegal_caption_characters)}";0;;;;0\n')
    
    def send_plu(self, plu):
        with open(self.tmp_filename, 'w') as file:
            if self.use_scancodes:
                for line in plu:
                    self._write_plu_line(file, line.code, line.caption, line.price, line.department)
            else:
                for i in range(1, self.number_of_plu + 1):
                    line = [line for line in plu if line.code == str(i)]
                    if line:
                        line = line[0]
                        self._write_plu_line(file, line.code, line.caption, line.price, line.department)
                    else:
                        self._write_plu_line(file, str(i), "", 0.00, 0)
        cmd = f'COMMAND=CPX\n'
        cmd += f'UPLOAD={self.tmp_filename}\n'
        if self.use_scancodes:
            cmd += 'COMMAND=CPM'
        with QDriver(self.ip_address, self.port) as q: q.run(cmd)
        self._clear_income_report()
        return True

    def send_mplu(self, plu):
        with open(self.tmp_filename, 'w') as file:
            for line in plu:
                if line.state in {'added', 'modified'}:
                    self._write_plu_line(file, line.code, line.caption, line.price, line.department)
                elif line.state == 'deleted':
                    if self.use_scancodes:
                        file.write(f'10000;-{line.code}\n')
                    else:
                        self._write_plu_line(file, line.code, "", 0.00, 0)
        cmd = f'UPLOAD={self.tmp_filename}\n'
        if self.use_scancodes: 
            cmd += 'COMMAND=CPB'
        with QDriver(self.ip_address, self.port) as q: q.run(cmd)
        return True
    
    def set_departments(self):
        with open(self.tmp_filename, 'w') as file:
            for i in range(1, self.number_of_departments + 1):
                department = [department for department in self.department_ids if department.code == i]
                if department:
                    department = department[0]
                    self._write_department_line(file, department.code, department.category_id.name)
                else:
                    self._write_department_line(file, str(i), "")
        with QDriver(self.ip_address, self.port) as q: q.upload_file(self.tmp_filename)
        return True

    def get_reports(self, clear=False):
        return(self._get_sales_report(clear), self._get_income_report(clear))    

    def clear_reports(self):
        self._clear_sales_report()
        self._clear_income_report()
        return True
