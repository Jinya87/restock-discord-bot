import unittest
from monitor import URLS, WATCHED, naver_status, newly_available

class NaverStockTests(unittest.TestCase):
    key = 'naver:nuclearclub:13697333976'
    title = '닌텐도 스위치2 엘든링 빛바랜 자 에디션 (한글판)'
    def control(self, text='구매하기', enabled=True, visible=True):
        return {'text': text, 'enabled': enabled, 'visible': visible}
    def status(self, text='', controls=None, title=None, url=None):
        return naver_status(self.key, url or URLS[self.key], title or self.title, text, controls or [])
    def test_six_requested_ids(self):
        self.assertEqual({u.split('/')[-1] for u in URLS.values()}, {'13698274396','13697333976','13733754793','13698276158','13734519413','13699099702'})
    def test_no_retired_alerts(self):
        self.assertEqual(newly_available({}, {'kurly:key': True,'hmall':True}), [])
    def test_sold_out_overrides_buy(self):
        self.assertFalse(self.status('현재 구매하실 수 없는 상품', [self.control()]))
        self.assertFalse(self.status('', [self.control(),self.control('품절되었습니다', False)]))
    def test_removed_product_is_unavailable(self):
        self.assertFalse(self.status('상품이 존재하지 않습니다'))
    def test_active_primary_buy(self):
        self.assertTrue(self.status('', [self.control()]))
    def test_disabled_buy_not_stock(self):
        with self.assertRaises(ValueError): self.status('', [self.control(enabled=False)])
    def test_hidden_buy_not_stock(self):
        with self.assertRaises(ValueError): self.status('', [self.control(visible=False)])
    def test_empty_panel_not_stock(self):
        with self.assertRaises(ValueError): self.status()
    def test_wrong_title_not_stock(self):
        with self.assertRaises(ValueError): self.status('', [self.control()], title='다른 게임')
    def test_wrong_url_not_stock(self):
        with self.assertRaises(ValueError): self.status('', [self.control()], url=URLS[self.key].replace('13697333976','123'))
    def test_security_and_network_error_not_stock(self):
        for text in ['Please complete the security verification.', '현재 서비스 접속이 불가합니다.']:
            with self.subTest(text=text), self.assertRaises(ValueError): self.status(text,[self.control()])
    def test_duplicate_and_restock(self):
        self.assertEqual(newly_available({self.key:True},{self.key:True}),[])
        self.assertEqual(newly_available({self.key:False},{self.key:True}),[self.key])
        self.assertEqual(newly_available({self.key:True},{}),[])
    def test_english_product_title(self):
        self.assertTrue(self.status('',[self.control()],title='[닌텐도 스위치2] ELDEN RING 빛바랜 자 에디션'))
if __name__ == '__main__': unittest.main()
