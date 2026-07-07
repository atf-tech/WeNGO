from django.test import SimpleTestCase

from receipt.views.helper import get_pdf_filename, get_template_name


class ReceiptTemplateSelectionTests(SimpleTestCase):
    def test_common_normal_receipt_template_is_used(self):
        self.assertEqual(get_template_name(""), "receipt/normal_receipt.html")

    def test_common_80g_receipt_template_is_used_when_pan_is_present(self):
        self.assertEqual(get_template_name("ABCDE1234F"), "receipt/80g_receipt.html")

    def test_pdf_filename_uses_80g_suffix_for_pan(self):
        self.assertEqual(
            get_pdf_filename("Jane Doe", "ABCDE1234F", "service"),
            "Jane_Doe_80g.pdf",
        )
