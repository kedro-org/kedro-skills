.PHONY: install lint type-check test build clean eval eval-skill eval-test eval-check-node

install:
	pip install -e ".[dev]"

lint:
	ruff check --fix src/ tests/
	ruff format src/ tests/

type-check:
	mypy src/

test:
	pytest tests/ -v

build:
	pip install build
	python -m build

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

# ---- Skill evals (see evals/) ----
# Needs Node >= 22.22 and API keys, either exported or in $(EVAL_ENV).
# Extra promptfoo flags go in ARGS, e.g.
#   make eval-skill SKILL=parameters-and-config ARGS="--filter-providers gpt-4o --filter-first-n 2"
PROMPTFOO ?= npx -y promptfoo@0.123.1
EVAL_ENV ?= evals/.env
EVAL_ENV_FLAG = $(if $(wildcard $(EVAL_ENV)),--env-file $(EVAL_ENV))
EVAL_RESULTS ?= evals/results
# promptfoo exits 100 when any test fails, baseline included. Failed tests exit
# 0 instead, and evals/lib/gate.js fails the run on with-skill results only.
# Config and provider errors still exit non-zero.
EVAL_RUN = PROMPTFOO_FAILED_TEST_EXIT_CODE=0 $(PROMPTFOO) eval $(EVAL_ENV_FLAG) $(ARGS)

eval-check-node:
	@node -e 'const [a,b]=process.versions.node.split(".").map(Number); if (a<22||(a===22&&b<22)) { console.error("Skill evals need Node >= 22.22, found " + process.versions.node); process.exit(1) }'

eval-test: eval-check-node
	node --test evals/lib/*.test.js

eval: eval-check-node eval-test
	@mkdir -p $(EVAL_RESULTS); status=0; for config in evals/skills/*/promptfooconfig.yaml; do \
		skill=$$(basename $$(dirname "$$config")); out="$(EVAL_RESULTS)/$$skill.json"; \
		echo "Evaluating: $$config"; rm -f "$$out"; \
		$(EVAL_RUN) -c "$$config" -o "$$out" && node evals/lib/gate.js "$$out" || status=1; \
	done; exit $$status

eval-skill: eval-check-node
	@test -n "$(SKILL)" || (echo "Usage: make eval-skill SKILL=<skill-id>"; exit 1)
	@mkdir -p $(EVAL_RESULTS); rm -f $(EVAL_RESULTS)/$(SKILL).json
	$(EVAL_RUN) -c evals/skills/$(SKILL)/promptfooconfig.yaml -o $(EVAL_RESULTS)/$(SKILL).json
	@node evals/lib/gate.js $(EVAL_RESULTS)/$(SKILL).json
