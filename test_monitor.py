import unittest
from monitor import kurly_rows, hmall_status, newly_available

class StockSafetyTests(unittest.TestCase):
    def rows(self, desk, key):
        return [{'text': f'{desk} 젤다의 전설 시간의 오카리나 (데스크패드) 88,000원', 'disabled': bool(desk)}, {'text': f'{key} 젤다의 전설 시간의 오카리나 (키캡키링) 88,000원', 'disabled': bool(key)}]

    def test_both_sold_out(self):
        self.assertEqual(kurly_rows(self.rows('(품절)', '(품절)')), {'kurly:key':False})

    def test_independent_options(self):
        self.assertEqual(kurly_rows(self.rows('', '(품절)')), {'kurly:key':False})

    def test_missing_option_is_error(self):
        with self.assertRaises(ValueError): kurly_rows(self.rows('', '')[:1])

    def test_hmall_suspended(self):
        self.assertFalse(hmall_status('현재 판매가 중단된 상품입니다.', '', False))

    def test_missing_button_not_restock(self):
        with self.assertRaises(ValueError): hmall_status('빈 페이지', '시간의 오카리나 아크릴 특전', False)

    def test_wrong_product_not_restock(self):
        with self.assertRaises(ValueError): hmall_status('구매하기', '다른 제품', True)

    def test_hmall_purchase_signal(self):
        self.assertTrue(hmall_status('구매하기', '시간의 오카리나 아크릴 특전', True))

    def test_hmall_sold_out_overrides_purchase_button(self):
        for text in ['품절되었습니다 구매하기', '일시 품절 바로구매', '품절 구매하기']:
            with self.subTest(text=text):
                self.assertFalse(hmall_status(text, '시간의 오카리나 아크릴 특전', True))

    def test_hmall_suspended_overrides_purchase_button(self):
        self.assertFalse(hmall_status('현재 판매가 중단된 상품입니다. 구매하기', '시간의 오카리나 아크릴 특전', True))

    def test_hmall_sold_out_without_button(self):
        self.assertFalse(hmall_status('품절되었습니다', '시간의 오카리나 아크릴 특전', False))

    def test_restock_and_no_duplicate(self):
        self.assertEqual(newly_available({'hmall': False}, {'hmall': True}), ['hmall'])
        self.assertEqual(newly_available({'hmall': True}, {'hmall': True}), [])

    def test_desk_never_notifies(self):
        self.assertEqual(newly_available({}, {'kurly:desk':True}), [])

    def test_unknown_preserves_previous(self):
        old = {'hmall':True, 'kurly:desk':False}
        old.update({'kurly:desk':False})
        self.assertEqual(newly_available(old, {'hmall':True}), [])

if __name__ == '__main__': unittest.main()
