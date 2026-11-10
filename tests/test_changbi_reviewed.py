import unittest
from build_changbi_reviewed import digest, validate


class ReviewGateTest(unittest.TestCase):
    def setUp(self):
        self.entry = dict(u='CB-00001', t='표제', a='홍길동', y=2000, l='통권 1호', s='요지다', h='해제다', kw=['문학'], c=[['주장이다', '주장']])
        self.body = '실제 본문을 처음부터 끝까지 읽은 뒤에야 공개 여부를 신중하게 판정한다.'
        self.meta = dict(in_scope=True, source='html', author='홍길동')
        self.screen = dict(status='queued', summary_hash=digest(self.entry), body_hash=digest(self.body))
        self.review = dict(self.screen, uid='CB-00001', status='pass', full_body_read=True, reviewer='test', reason='전체 대조')

    def check(self, review=None):
        return validate(self.entry, self.meta, self.screen, self.review if review is None else review, self.body)

    def test_verified(self):
        self.assertIsNone(self.check())

    def test_no_review(self):
        self.assertIsNotNone(validate(self.entry, self.meta, self.screen, None, self.body))

    def test_changed_summary(self):
        self.entry['h'] += '바뀜'
        self.assertIsNotNone(self.check())

    def test_changed_body(self):
        self.body += '바뀜'
        self.assertIsNotNone(self.check())

    def test_held(self):
        self.review['status'] = 'hold'
        self.assertIsNotNone(self.check())

    def test_not_fully_read(self):
        self.review['full_body_read'] = False
        self.assertIsNotNone(self.check())

    def test_verbatim(self):
        self.entry['h'] = self.body
        self.screen['summary_hash'] = self.review['summary_hash'] = digest(self.entry)
        self.assertIsNotNone(self.check())

    def test_private_email(self):
        self.entry['kw'] = ['private@example.com']
        self.screen['summary_hash'] = self.review['summary_hash'] = digest(self.entry)
        self.assertIsNotNone(self.check())

    def test_scope(self):
        self.screen.update(status='held', reasons=['보류'])
        self.assertIsNotNone(self.check())


if __name__ == '__main__':
    unittest.main()
