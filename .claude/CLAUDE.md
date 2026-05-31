# devlog
- **devlog** (`~/.claude/skills/devlog/SKILL.md`) - 대화에서 발생한 이벤트(질문, 결정, 학습, 진행)를 `devlog/` 디렉토리에 카테고리별로 기록. Trigger: `/devlog`
When the user types `/devlog`, invoke the Skill tool with `skill: "devlog"` before doing anything else.

# lint
- **lint** (`~/.claude/skills/lint/SKILL.md`) - ASTER 프로젝트 설계 문서(docs/)와 소스 코드(src/) 간 필드명, 라우팅, 프롬프트 변수, 설정값 일관성 교차 검증. 위험도 순(CRITICAL/WARNING/INFO)으로 이슈 보고. Trigger: `/lint`
When the user types `/lint`, invoke the Skill tool with `skill: "lint"` before doing anything else.
