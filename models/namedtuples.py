# -*- coding: utf-8 -*-

from collections import namedtuple

Plu = namedtuple("Plu", ["code", "caption", "price", "department", "state"])
SalesReport = namedtuple("SalesReport", ["code", "quantity"])
IncomeReport = namedtuple("IncomeReport", ["code", "total"])
