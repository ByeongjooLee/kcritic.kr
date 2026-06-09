import json

data = json.loads(open("site/data/thinkers.json", encoding="utf-8").read())

print("이름                     | 비평글 | 문맥 | 비율")
print("-" * 55)
no_ctx = []
low_ctx = []
for t in sorted(data, key=lambda x: -x["essay_count"]):
    ratio = t["context_count"] / t["essay_count"] if t["essay_count"] > 0 else 0
    flag = " <<<" if t["context_count"] == 0 else (" <<" if ratio < 0.3 else ("" if ratio >= 0.5 else " <"))
    name = t["name"][:20]
    print(f"{name:22s} | {t['essay_count']:3d} | {t['context_count']:3d} | {ratio:.1f}{flag}")
    if t["context_count"] == 0:
        no_ctx.append(t["name"])
    elif ratio < 0.5 and t["essay_count"] >= 2:
        low_ctx.append((t["name"], t["id"], t["essay_count"], t["context_count"]))

print()
print(f"문맥 0건: {len(no_ctx)}명")
for n in no_ctx:
    print(f"  - {n}")
print()
print(f"문맥 비율 50% 미만 (2편 이상): {len(low_ctx)}명")
for name, pid, ec, cc in low_ctx:
    print(f"  - {name} ({pid}): {ec}편 중 {cc}건")
