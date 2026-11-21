# 참여하기 제안을 Gemini(Google)로 넘길 때 제안자의 이름·전자우편·소속이 나가지 않는지 본다.
# 실행(저장소 루트에서): py -X utf8 -m unittest tests.test_contribute_privacy
# 실제 Gemini 는 부르지 않는다 — urllib.request.urlopen 을 가로채 보낸 내용을 본다.
import io
import json
import os
import unittest
from unittest import mock

os.environ.setdefault("GEMINI_API_KEY", "")
try:
    import neo4j_api
except Exception as e:            # fastapi·neo4j·anthropic 이 없는 컴퓨터
    raise unittest.SkipTest(f"neo4j_api 를 불러오지 못함: {e}")

NAME, EMAIL, AFFIL = "홍길동-제안자", "submitter@example.org", "가나다대학교 국어국문학과"


def record(i, detail):
    return {
        "id": f"id{i:04d}", "submitted_at": "2026-11-22T00:00:00", "status": "pending",
        "type": "fix_person", "name": NAME, "email": EMAIL, "affiliation": AFFIL,
        "summary": "요약", "detail": detail, "source": "출처",
    }


class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def gemini_reply(payload):
    text = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
    return FakeResponse(json.dumps({"candidates": [{"content": {"parts": [{"text": text}]}}]}).encode())


class GeminiPayloadTest(unittest.TestCase):
    def setUp(self):
        self.records = [record(0, "<persName>김현</persName> 1962년"), record(1, "둘째 제안")]

    def call(self, reply):
        sent = {}

        def fake_urlopen(req, timeout=None):
            sent["url"], sent["body"] = req.full_url, req.data.decode("utf-8")
            if isinstance(reply, Exception):
                raise reply
            return gemini_reply(reply)

        with mock.patch.object(neo4j_api, "GEMINI_KEY", "test-key"), \
             mock.patch.object(neo4j_api.urllib.request, "urlopen", fake_urlopen):
            out = neo4j_api.gemini_normalize(self.records)
        return sent, out

    def test_only_type_and_detail_leave_the_server(self):
        self.assertEqual(neo4j_api.GEMINI_FIELDS, ("type", "detail"))
        sent, _ = self.call([])
        text = json.loads(sent["body"])["contents"][0]["parts"][0]["text"]
        for secret in (NAME, EMAIL, AFFIL, "id0000", "2026-11-22T00:00:00", "요약", "출처"):
            self.assertNotIn(secret, text)
            self.assertNotIn(secret, sent["url"])
        self.assertIn("김현", text)          # 서식을 맞출 내용은 간다
        for row in neo4j_api._gemini_payload(self.records):
            self.assertEqual(sorted(row), ["detail", "n", "type"])

    def test_only_detail_comes_back(self):
        _, out = self.call([
            {"n": 0, "type": "other", "detail": "<persName xml:id=\"p-x\" role=\"critic\">김현</persName> 1962",
             "name": "바뀐 이름", "email": "evil@example.org", "status": "approved"},
        ])
        self.assertIn("xml:id", out[0]["detail"])
        self.assertEqual(out[1]["detail"], "둘째 제안")       # 돌려주지 않은 항목은 그대로
        for o, r in zip(out, self.records):
            for k in ("id", "submitted_at", "status", "type", "name", "email", "affiliation", "summary", "source"):
                self.assertEqual(o[k], r[k], k)

    def test_bad_replies_keep_the_original(self):
        bad = [
            {"oops": 1},                                   # 배열이 아님
            [{"n": 5, "detail": "범위 밖"}, {"n": "0", "detail": "순번이 글자"}, {"n": True, "detail": "참"}, "글자"],
            [{"n": 0, "detail": ""}, {"n": 1, "detail": "가" * (neo4j_api.DETAIL_MAX + 1)}, {"n": 0, "detail": ["목록"]}],
            OSError("연결 실패"),
        ]
        for reply in bad:
            _, out = self.call(reply)
            self.assertEqual(out, self.records, repr(reply)[:60])

    def test_no_key_means_nothing_is_sent(self):
        def boom(*a, **k):
            raise AssertionError("키가 없는데 Gemini 를 불렀다")
        with mock.patch.object(neo4j_api, "GEMINI_KEY", ""), \
             mock.patch.object(neo4j_api.urllib.request, "urlopen", boom):
            self.assertEqual(neo4j_api.gemini_normalize(self.records), self.records)


if __name__ == "__main__":
    unittest.main()
