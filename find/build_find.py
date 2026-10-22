# -*- coding: utf-8 -*-
"""글 찾기 색인 (사이트용) — bge-m3 로컬 ONNX(GPU)로 계산. build.py → build_site_v2.py 다음에 실행.

공개 (site/data/find/, 메타데이터에서만 만든 것)
  meta.json   글 id 순서, 어휘(개념어 2편 이상 + 인물), 행 수
  vec.bin     int8 행렬 [글 전체 N + 제목 N + 개념어 N + 인물 N] × 1024 → 뒤에 float32 행별 배율
  vocab.bin   int8 [어휘 V] × 1024 → 뒤에 float32 배율
비공개 (worker/private/ — .gitignore·.assetsignore, Worker 번들에만 들어감)
  bodylex/NNN.txt  본문 희귀어 역색인 256조각. 줄 = 낱말\t글번호,글번호…  (본문 25편 이하에만 나오는 낱말)
                   조각 번호 = FNV-1a(UTF-16 코드 단위) % 256 — worker/index.js 와 같아야 한다

본문 원문·본문 구간 벡터는 내보내지 않는다(원문 보호, CLAUDE.md §1).
실행: <ocr_train venv python> -X utf8 find/build_find.py
"""
import os, sys, json, re, time, collections
import torch  # noqa: F401  onnxruntime-gpu 가 CUDA DLL 을 찾도록
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\hgohg\Downloads\drive-download-20260918T092441Z-1-002\작업도구\추천")
from embed_local_bge import LocalBGE  # noqa: E402

PUB = os.path.join(REPO, "site", "data", "find")
PRIV = os.path.join(REPO, "worker", "private", "bodylex")
os.makedirs(PUB, exist_ok=True); os.makedirs(PRIV, exist_ok=True)
NSHARD, MAX_DF = 256, 25
PARTS = sorted(["으로서", "으로", "에서", "에게", "에는", "에서의", "이라는", "라는", "과의", "와의", "이란", "란", "은", "는", "이", "가",
                "을", "를", "의", "과", "와", "도", "로", "에", "만", "들", "이다", "이며", "하는", "하고", "했다", "한다", "에서는", "으로는",
                "이나", "나", "께서", "처럼", "보다", "부터", "까지"], key=len, reverse=True)


def strip_particle(w):
    for p in PARTS:
        if w.endswith(p) and len(w) - len(p) >= 2: return w[:-len(p)]
    return w


def fnv(word):
    h = 0x811C9DC5
    for ch in word.encode("utf-16-le").decode("utf-16-le"):
        for unit in ([ord(ch)] if ord(ch) < 0x10000 else [0xD800 + ((ord(ch) - 0x10000) >> 10), 0xDC00 + ((ord(ch) - 0x10000) & 0x3FF)]):
            h ^= unit; h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def q8(M):
    M = np.asarray(M, np.float32)
    s = (np.abs(M).max(axis=1) / 127.0).astype(np.float32); s[s == 0] = 1
    return np.round(M / s[:, None]).astype(np.int8), s


def write_bin(path, M):
    q, s = q8(M)
    with open(path, "wb") as f:
        f.write(q.tobytes()); f.write(s.astype("<f4").tobytes())


def main():
    t0 = time.time()
    essays = json.load(open(os.path.join(REPO, "site/data/v2/essays.json"), encoding="utf-8"))
    people = {p["id"]: p["name"] for p in json.load(open(os.path.join(REPO, "site/data/v2/people.json"), encoding="utf-8"))}
    nm = lambda i: people.get(i, "")
    M = LocalBGE(max_len=512)

    def doc_text(e):
        parts = [f"제목: {e['title']}", f"필자: {e['critic_name']}", f"연도: {e['year']}",
                 "지면: " + (f"문학과사회 {e['issue']}호 {e['section']}" if e["coll"] == "mhs" else e["venue"])]
        if e["concepts"]: parts.append("개념어: " + ", ".join(e["concepts"]))
        if e["subjects"]: parts.append("다룬 작가: " + ", ".join(filter(None, map(nm, e["subjects"]))))
        if e["theorists"]: parts.append("인용 이론가: " + ", ".join(filter(None, map(nm, e["theorists"]))))
        return "\n".join(parts)

    def ppl(e):
        s = []
        if e["subjects"]: s.append("다룬 작가: " + ", ".join(filter(None, map(nm, e["subjects"]))))
        if e["theorists"]: s.append("인용 이론가: " + ", ".join(filter(None, map(nm, e["theorists"]))))
        return " / ".join(s) or e["title"]

    D = M.encode([doc_text(e) for e in essays], batch=16)
    M.tok.enable_truncation(256)
    F = [M.encode([e["title"] for e in essays], batch=32),
         M.encode(["개념어: " + ", ".join(e["concepts"]) if e["concepts"] else e["title"] for e in essays], batch=32),
         M.encode([ppl(e) for e in essays], batch=32)]
    write_bin(os.path.join(PUB, "vec.bin"), np.vstack([D] + F))
    print(f"vec {len(essays)}×4 {time.time()-t0:.0f}s")

    cnt = collections.Counter()
    for e in essays:
        for c in set(e["concepts"]): cnt[("c", c)] += 1
        for pid in set(e["subjects"] + e["theorists"] + [e["critic"]]):
            if nm(pid): cnt[("p", pid)] += 1
    vocab = [(k, v, n) for (k, v), n in sorted(cnt.items(), key=lambda x: (-x[1], x[0])) if k == "p" or n >= 2]
    terms = [v if k == "c" else nm(v) for k, v, n in vocab]
    W = M.encode(terms, batch=64)
    write_bin(os.path.join(PUB, "vocab.bin"), W)
    print(f"vocab {len(terms)} {time.time()-t0:.0f}s")

    json.dump({"ids": [e["id"] for e in essays], "dim": 1024, "rows": len(essays) * 4, "layers": ["doc", "title", "concepts", "people"],
               "vocab": {"terms": terms, "kinds": [("c" if k == "c" else "p:" + v) for k, v, n in vocab], "df": [n for k, v, n in vocab]},
               "nshard": NSHARD, "max_df": MAX_DF, "model": "@cf/baai/bge-m3", "built": time.strftime("%Y-%m-%d %H:%M")},
              open(os.path.join(PUB, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    df = collections.defaultdict(set)
    for i, e in enumerate(essays):
        p = os.path.join(REPO, "essays", e["id"] + ".txt")
        if not os.path.exists(p): continue
        for w in re.findall(r"[가-힣A-Za-z0-9·]{2,}", open(p, encoding="utf-8").read()):
            w = w.strip("·")
            if len(w) < 2 or w.isdigit(): continue
            df[w].add(i)
            s = strip_particle(w)
            if s != w and len(s) >= 2: df[s].add(i)
    shards = [[] for _ in range(NSHARD)]
    for w, d in df.items():
        if len(d) <= MAX_DF and "\t" not in w and "\n" not in w:
            shards[fnv(w) % NSHARD].append(w + "\t" + ",".join(map(str, sorted(d))))
    for k, lines in enumerate(shards):
        with open(os.path.join(PRIV, f"{k:03d}.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n" + "\n".join(sorted(lines)) + "\n")
    with open(os.path.join(REPO, "worker", "private", "shards.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write("// find/build_find.py 가 만든다. 본문 희귀어 역색인 조각 — 공개 저장소에 올리지 말 것\n")
        for k in range(NSHARD): f.write(f'import s{k:03d} from "./bodylex/{k:03d}.txt";\n')
        f.write("export default [" + ",".join(f"s{k:03d}" for k in range(NSHARD)) + "];\n")
    print(f"bodylex {sum(len(s) for s in shards)} words → {NSHARD} shards {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
