# SETUP — 다른 컴퓨터에서 이어서 작업하기

이 프로젝트를 새 컴퓨터에서 세팅하는 방법. (레포: `https://github.com/ByeongjooLee/kcritic.kr`)

---

## 0. 무엇이 git에 있고, 무엇이 없나

| 구분 | git 포함 | 비고 |
|---|---|---|
| 코드·사이트 산출물 | ✅ | build.py, *.html, site/**, style.css, id_map.json, persons.json 등 |
| **essays/*.xml, *.txt** (원문) | ❌ | 저작권 — git·배포 제외. **재빌드하려면 따로 옮겨야 함** |
| **.env** (API 키) | ❌ | 부가 기능(GraphRAG·크라우드소싱)에만 필요. `.env.example` 참고 |
| node_modules | ❌ | `npm install` 로 복원 |
| 작업 산출물 (*.bak, qid_fix_*.csv 등) | ❌ | 불필요 |

> ⚠️ **핵심:** `git clone` 만으로는 **사이트 배포는 되지만 재빌드(py build.py)는 안 됨** — `essays/` 원문이 없어서. 원문은 OneDrive 동기화 또는 수동 복사로 옮긴다.

---

## 1. 필수 도구 설치 (Windows)

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id GitHub.cli -e
```

설치 후 **새 PowerShell 창**을 열어 PATH 반영. 확인:
```powershell
git --version; py --version; node --version; gh --version
```

---

## 2. 코드 받기 — 두 가지 방법

### 방법 A. OneDrive 동기화 (가장 쉬움, 원문·.env 자동 포함)
같은 OneDrive 계정으로 로그인하면 `문서\대학원 공부\박사이후 논문 투고\온톨로지\` 폴더 전체(essays·.env·부모 데이터 포함)가 자동 동기화된다. 동기화 완료 후 3번으로.

### 방법 B. git clone (원문·.env는 별도 이전 필요)
```powershell
git clone https://github.com/ByeongjooLee/kcritic.kr.git critic-ontology
cd critic-ontology
```
그 다음 아래를 **수동으로 채워 넣는다**(OneDrive·USB·백업에서 복사):
- `essays/` 폴더의 `*.xml`, `*.txt` — 재빌드(인코딩 작업)에 필수
- `.env` — `cp .env.example .env` 후 값 채우기(부가 기능용, 사이트 배포엔 불필요)
- (선택) `..\Person_rdf_20260401\` — 인물 NLK 검증 스크립트용(대용량)
- (선택) 부모 폴더 xlsx (박사논문 등) — `convert_phd.py` 용

---

## 3. 의존성 설치

```powershell
# Python (변환·API 스크립트용; build.py 자체는 표준 라이브러리만 사용해 없어도 빌드 가능)
py -m pip install openpyxl neo4j fastapi "uvicorn[standard]" anthropic python-dotenv pydantic

# Node (SPARQL 번들 재생성·배포 도구)
npm install
```

---

## 4. 인증 (한 번만)

```powershell
gh auth login              # GitHub — push 권한 (HTTPS + 웹 브라우저 인증)
npx wrangler login         # Cloudflare — 배포 권한
```
확인: `gh auth status`, `npx wrangler whoami`

---

## 5. 일상 작업

```powershell
# 사이트 재빌드 (essays/ 원문 있어야 함)
py build.py

# 빌드 → 커밋 → 푸시 → Cloudflare 라이브 배포 (한 방)
.\deploy.ps1 "커밋 메시지"
```

> `git push` 만으로는 **라이브 반영 안 됨** — 반드시 `npx wrangler deploy`(deploy.ps1이 포함). 자세한 내용은 `CLAUDE.md` §10.

### 인물 데이터 검증 스크립트 (필요 시)
```powershell
py verify_lod.py            # Wikidata QID 역검증
py verify_encykorea.py      # encykorea ↔ Wikidata P9475 교차검증
py enrich_en_names.py       # 외국 인물 영문명 보강
```
(모두 미리보기 우선, `--apply` 로 persons.json 반영. 백업 자동 생성.)

---

## 6. 주의사항 (CLAUDE.md 요약)

- **`essays/*.xml`·`.env`·`*.bak`·`essays_backup*` 절대 커밋·배포 금지** (`.gitignore`·`.assetsignore`가 막지만 `git add -A` 시 확인)
- PowerShell git 커밋 메시지는 **ASCII** 권장 (한글 here-string 파싱 오류)
- 빌드 결정성: set은 `sorted()`, count 정렬엔 tiebreaker (2회 빌드 후 diff 0 확인)
- LOD 링크 추가는 build.py `LOD_SOURCES` 한 곳 + persons.json 필드
- 작업 지침 전체는 **`CLAUDE.md`** 참조 (AI 어시스턴트·사람 공통)

---

## 7. 빠른 점검 (세팅 후)

```powershell
py build.py                                   # 빌드 성공?
py build.py; # 한 번 더 → git diff 가 비어야 결정적
git status                                    # 원문·.env 안 잡혔는지
npx wrangler whoami                           # 배포 인증됐는지
```
