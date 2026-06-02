# Git Branch 전략 및 PR 가이드

이 프로젝트는 **GitHub Flow**를 사용한다.

```
feat/기능A ──┐
fix/버그B   ──┼──→ master
docs/문서C  ──┘
```

모든 작업은 master에서 분기한 작업 브랜치에서 진행하고, PR을 통해 master에 병합한다. master는 항상 실행 가능한 상태를 유지한다.

> Git Flow(develop 브랜치 포함)와 달리 중간 통합 브랜치가 없다. 1인 프로젝트에서 배포 사이클이 짧고 단순한 경우에 적합하다.

---

## 브랜치 명명 규칙

브랜치 이름은 `타입/설명` 형식으로 작성하며 소문자와 하이픈(`-`)만 사용한다.

| 타입 | 용도 | 예시 |
|---|---|---|
| `feat/` | 새로운 기능 구현 | `feat/graphrag-relational-graph` |
| `fix/` | 버그 및 오류 수정 | `fix/qdrant-domain-filter` |
| `docs/` | 문서 작성 및 수정 | `docs/state-definition-update` |
| `refactor/` | 기능 변경 없는 코드 구조 개선 | `refactor/llm-singleton-utils` |
| `test/` | 테스트 코드 추가 및 수정 | `test/critic-reflection-loop` |
| `chore/` | 빌드, 패키지, 설정 파일 변경 | `chore/docker-compose-setup` |

```
feat/graphrag-relational-graph  ✅ 소문자, 하이픈 구분
fix/qdrant-domain-filter        ✅
feat/GraphRAG                   ❌ 카멜케이스 금지
feat/그래프수정                  ❌ 한국어 금지
feat/fix2                       ❌ 너무 추상적
```

---

## 작업 흐름

```bash
# 1. master 최신 상태로 업데이트
git checkout master
git pull origin master

# 2. 작업 브랜치 생성
git checkout -b feat/graphrag-relational-graph

# 3. 작업 후 커밋 (commit 컨벤션 참고)
git commit -m "feat: aspect-opinion-sentiment 관계 그래프 build_graph 구현"

# 4. 원격에 push
git push origin feat/graphrag-relational-graph

# 5. GitHub에서 PR 생성 → 셀프 리뷰 → merge

# 6. merge 완료 후 로컬 브랜치 삭제
git checkout master
git pull origin master
git branch -d feat/graphrag-relational-graph
```

원격에서 삭제된 브랜치가 계속 보이면 `--prune`으로 정리한다.

```bash
git fetch --prune

# 매번 자동 정리하려면
git config --global fetch.prune true
```

---

## PR 가이드

### PR 제목

커밋 컨벤션과 동일하게 `타입: 내용` 형식으로 작성한다.

```
feat: aspect-opinion-sentiment 관계 그래프 구현
fix: vector_rag domain 필터 누락 수정
docs: state_definition 필드 테이블 보강
```

### PR 본문 템플릿

```markdown
## 작업 내용

- [ ] [구현 항목 1]
- [ ] [구현 항목 2]
- [ ] [구현 항목 3]

## 변경 이유

[기존 방식의 문제점, 또는 새 기능이 필요한 이유]

## 테스트 방법

1. [실행 방법]
2. [확인 방법]
3. [예상 결과]
```

### 셀프 리뷰 방법

PR 생성 후 본인이 직접 "Files changed" 탭에서 변경 내용을 확인한다. 코드 줄에 직접 댓글을 달아 메모를 남길 수 있다. 댓글 앞에 아래 태그를 붙이면 나중에 히스토리를 볼 때 의도가 명확해진다.

| 태그 | 의미 |
|---|---|
| `[필수]` | 반드시 수정해야 merge 가능 |
| `[제안]` | 수정하면 더 좋지만 선택사항 |
| `[질문]` | 이해가 안 돼서 메모해두는 것 |

### merge 방법

**Create a merge commit**을 사용한다. "피처 브랜치가 어느 시점에 master에 들어왔는지" 기록이 남아 히스토리 추적이 쉽다. merge 후 GitHub에서 "Delete branch" 버튼으로 브랜치를 삭제한다.

---

## 주의사항

- **단일 책임**: 하나의 브랜치가 여러 기능을 동시에 수정하지 않는다
- **수시 커밋**: 논리적으로 완결된 단위마다 커밋. 하나의 커밋이 너무 크면 리뷰가 어렵다
- **병합 전 테스트**: `docker compose run --rm app python main.py` 정상 동작 확인 후 merge
- **master 직접 커밋 금지**: 반드시 브랜치 → PR → merge 순서를 지킨다
- **merge 완료 브랜치 즉시 삭제**: 오래된 브랜치 방치 금지

---

## 치트시트

```
새 기능:    master → feat/기능명 분기 → 작업 → PR → master merge
버그 수정:  master → fix/버그내용 분기 → 수정 → PR → master merge
문서:       master → docs/내용 분기 → 작성 → PR → master merge

브랜치 네이밍:
  feat/graphrag-relational-graph  ✅
  fix/qdrant-domain-filter        ✅
  feat/GraphRAG                   ❌ 카멜케이스
  feat/그래프수정                  ❌ 한국어

절대 금지:
  ❌ master에 직접 커밋/push
  ❌ 공유 브랜치에 force push
  ❌ PR 없이 merge
  ❌ 오래된 브랜치 방치
```
