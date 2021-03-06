# Copyright 2016 Akretion Mourad EL HADJ MIMOUNE
# Copyright 2020 Hibou Corp.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import common

from .common import setup_test_model
from .purchase_test import LineTest, PurchaseTest

_logger = logging.getLogger(__name__)


@common.tagged("post_install", "-at_install")
class TestBaseException(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestBaseException, cls).setUpClass()
        setup_test_model(cls.env, [PurchaseTest, LineTest])

        cls.base_exception = cls.env["base.exception"]
        cls.exception_rule = cls.env["exception.rule"]
        if "test_purchase_ids" not in cls.exception_rule._fields:
            field = fields.Many2many("base.exception.test.purchase")
            cls.exception_rule._add_field("test_purchase_ids", field)
            cls.exception_rule._fields["test_purchase_ids"].depends_context = None
        cls.exception_confirm = cls.env["exception.rule.confirm"]
        cls.exception_rule._fields["model"].selection.append(
            ("base.exception.test.purchase", "Purchase Order")
        )

        cls.exception_rule._fields["model"].selection.append(
            ("base.exception.test.purchase.line", "Purchase Order Line")
        )

        cls.exceptionnozip = cls.env["exception.rule"].create(
            {
                "name": "No ZIP code on destination",
                "sequence": 10,
                "model": "base.exception.test.purchase",
                "code": "if not self.partner_id.zip: failed=True",
            }
        )

        cls.exceptionno_minorder = cls.env["exception.rule"].create(
            {
                "name": "Min order except",
                "sequence": 10,
                "model": "base.exception.test.purchase",
                "code": "if self.amount_total <= 200.0: failed=True",
            }
        )

        cls.exceptionno_lineqty = cls.env["exception.rule"].create(
            {
                "name": "Qty > 0",
                "sequence": 10,
                "model": "base.exception.test.purchase.line",
                "code": "if obj.qty <= 0: failed=True",
            }
        )

    def test_purchase_order_exception(self):
        partner = self.env.ref("base.res_partner_1")
        partner.zip = False
        potest1 = self.env["base.exception.test.purchase"].create(
            {
                "name": "Test base exception to basic purchase",
                "partner_id": partner.id,
                "line_ids": [
                    (0, 0, {"name": "line test", "amount": 120.0, "qty": 1.5})
                ],
            }
        )
        # Block because of exception during validation
        with self.assertRaises(ValidationError):
            potest1.button_confirm()
        # Test that we have linked exceptions
        self.assertTrue(potest1.exception_ids)
        # Test ignore exeception make possible for the po to validate
        potest1.action_ignore_exceptions()
        self.assertTrue(potest1.ignore_exception)
        self.assertFalse(potest1.exceptions_summary)
        potest1.button_confirm()
        self.assertTrue(potest1.state == "purchase")

    def test_purchase_order_exception_blocking(self):
        self.exceptionnozip.is_blocking = True
        partner = self.env.ref("base.res_partner_1")
        partner.zip = False
        potest1 = self.env["base.exception.test.purchase"].create(
            {
                "name": "Test base exception to basic purchase",
                "partner_id": partner.id,
                "line_ids": [
                    (0, 0, {"name": "line test", "amount": 120.0, "qty": 1.5})
                ],
            }
        )
        # Block because of exception during validation
        with self.assertRaises(ValidationError):
            potest1.button_confirm()
        # Test that we have linked exceptions
        self.assertTrue(potest1.exception_ids)
        self.assertTrue(potest1.exceptions_summary)
        # Test cannot ignore blocked exception
        with self.assertRaises(UserError):
            potest1.action_ignore_exceptions()
        self.assertFalse(potest1.ignore_exception)
        with self.assertRaises(ValidationError):
            potest1.button_confirm()
        self.assertTrue(potest1.exception_ids)
        self.assertTrue(potest1.exceptions_summary)
