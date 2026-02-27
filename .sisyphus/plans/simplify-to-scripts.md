# Simplify Canvas Scraper to Simple Scripts

## TL;DR

> **Quick Summary**: Strip the over-engineered Python package layer, CI/CD, Docker, and build system from the canvas-scraper repo while preserving the 10 working simple scripts. Fix the broken WSL scheduling, remove the GUI setup wizard, and add basic smoke tests.
> 
> **Deliverables**:
> - Clean repo with only working simple scripts in `src/`
> - Working WSL Task Scheduler integration (no hang, actually runs)
> - CLI-only setup wizard (no tkinter/GUI)
> - Basic smoke tests with mocks
> - Updated README reflecting simplified project
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (delete cruft) -> Task 3 (remove GUI) -> Task 5 (fix WSL) -> Task 8 (smoke tests) -> Task 9 (README)

---

## Context

### Original Request
User wants to "revert this repo to simple scripts" — the canvas scraper should run at a fixed time every day, download files on the user's computer, and send email notifications. All of these features already work in the simple scripts layer; the repo just needs cleanup.

### Interview Summary
**Key Discussions**:
- Simplification scope: "Delete cruft only" — keep the 10 working scripts in `src/`, remove the duplicated `src/canvas_scraper/` package
- GUI: Remove `gui_setup.py` — CLI setup wizard in `main.py` stays
- Scheduling: WSL scheduling is the key bug — "doesn't hang but doesn't work"
- Tests: Add basic smoke tests for critical paths (Canvas connection, email, config)

**Research Findings**:
- `src/canvas_scraper/` is a 21-file, ~3,900-line duplicate of the 10 simple scripts — zero cross-imports
- The simple scripts import nothing from `canvas_scraper` — deletion is safe
- WSL scheduling chain: Task Scheduler -> wsl.exe -> bash -c -> cd -> run_with_timeout.sh -> timeout -> python
- Multiple WSL bugs identified: missing `--distribution` flag, unreliable `wsl pwd`, no output redirection at outer level, venv path mismatch (both `.venv/` and `venv/` exist)
- `tests/conftest.py` imports from `canvas_scraper` — will break, must be deleted with the package

### Metis Review
**Identified Gaps** (addressed):
- `conftest.py` dependency on `canvas_scraper` — resolved: delete entire `tests/` and recreate in smoke test task
- `pyproject.toml` points pytest/coverage at deleted package — resolved: strip to minimal tool config
- `uv.lock` will be stale — resolved: delete it
- `run_with_timeout.sh` hardcodes `./venv/bin/python` but `.venv/` also exists — resolved: make venv detection flexible
- Version inconsistency (`1.1.0` in src/__init__.py, `2.0.0` in pyproject.toml) — resolved: set to `1.2.0`
- Smoke tests need mocking strategy — resolved: use unittest.mock, no real credentials

---

## Work Objectives

### Core Objective
Remove all over-engineered artifacts (package, build system, CI/CD, Docker, GUI) while preserving the working simple scripts, fix the broken WSL daily scheduling, and add basic test coverage.

### Concrete Deliverables
- Cleaned repo: only `src/*.py` scripts, config files, templates, scheduler scripts
- Fixed `setup_scheduler.ps1` with proper WSL distro detection, path handling, output redirection
- Fixed `run_with_timeout.sh` with flexible venv detection
- `tests/` directory with smoke tests using mocks
- Updated `README.md` and `QUICKSTART.md`

### Definition of Done
- [x] `python -c "import sys; sys.path.insert(0, 'src'); import main"` succeeds
- [x] `python src/main.py --dry-run` runs without import errors (may fail on config — that's OK)
- [x] `python -m pytest tests/ -v` — all tests pass
- [x] No references to `canvas_scraper`, `gui_setup`, `build_exe`, `Dockerfile` in `src/*.py` or `README.md`
- [x] WSL Task Scheduler task registers and executes (verified by user on Windows)

### Must Have
- All 10 simple scripts in `src/` untouched (except `main.py` GUI removal)
- `requirements.txt` as sole dependency source (7 packages, no pydantic/structlog/tenacity)
- Working `setup_scheduler.sh` and `setup_scheduler.ps1`
- Working `run_with_timeout.sh`
- Email HTML template in `templates/` preserved
- `config.yaml`, `config.example.yaml`, `.env.example` preserved

### Must NOT Have (Guardrails)
- DO NOT modify Canvas API logic, download logic, email logic, filter logic, or any core behavior
- DO NOT consolidate/merge the 10 scripts into fewer files — "delete cruft only"
- DO NOT add new features or dependencies
- DO NOT change `config.yaml` format or `.env` variable names
- DO NOT write integration tests that require real Canvas/email credentials
- DO NOT rewrite the entire README — only update affected sections
- DO NOT touch `templates/email_report.html` or `data/` directory

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.
> Exception: WSL Task Scheduler testing requires Windows machine — provide exact verification commands as instructions.

### Test Decision
- **Infrastructure exists**: NO (empty scaffold being replaced)
- **Automated tests**: Tests-after (smoke tests in Phase 4)
- **Framework**: pytest (already in requirements, keep pyproject.toml config)

### QA Policy
Every task includes agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **File operations**: Use Bash — verify deletions, check imports, run dry-run
- **WSL/PowerShell**: Provide exact commands as verification scripts (user runs on Windows)
- **Tests**: Use Bash — `python -m pytest tests/ -v`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — independent cleanup):
├── Task 1: Delete over-engineered package and build artifacts [quick]
├── Task 2: Strip pyproject.toml to minimal tool config [quick]
└── Task 3: Remove GUI setup wizard from main.py [quick]

Wave 2 (After Wave 1 — scheduling fix + tests):
├── Task 4: Fix run_with_timeout.sh venv detection [quick]
├── Task 5: Fix WSL scheduling in setup_scheduler.ps1 [deep]
├── Task 6: Write smoke tests [unspecified-high]
└── Task 7: Update .gitignore and clean tracked artifacts [quick]

Wave 3 (After Wave 2 — documentation + final verification):
├── Task 8: Update README.md and QUICKSTART.md [quick]
└── Task 9: Final integration verification [deep]

Wave FINAL (After ALL tasks — independent review):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Import and runtime QA [unspecified-high]
└── Task F4: Scope fidelity check [deep]

Critical Path: Task 1 → Task 3 → Task 5 → Task 6 → Task 8 → Task 9 → F1-F4
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 3 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 (Delete package) | — | 3, 4, 5, 6, 7, 8 |
| 2 (Strip pyproject) | — | 6, 7 |
| 3 (Remove GUI) | 1 | 6, 8, 9 |
| 4 (Fix timeout.sh) | 1 | 5, 9 |
| 5 (Fix WSL PS1) | 4 | 9 |
| 6 (Smoke tests) | 1, 2, 3 | 9 |
| 7 (Gitignore/clean) | 1, 2 | 9 |
| 8 (Update README) | 1, 3, 5 | 9 |
| 9 (Integration verify) | ALL 1-8 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 → `quick`, T2 → `quick`, T3 → `quick`
- **Wave 2**: 4 tasks — T4 → `quick`, T5 → `deep`, T6 → `unspecified-high`, T7 → `quick`
- **Wave 3**: 2 tasks — T8 → `quick`, T9 → `deep`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Delete over-engineered package and build artifacts

  **What to do**:
  - Delete the entire `src/canvas_scraper/` directory (21 files, ~3,900 lines)
  - Delete `build/` and `dist/` directories (build artifacts)
  - Delete `build_exe.py` (PyInstaller build script)
  - Delete `canvas-scraper.spec` (PyInstaller spec)
  - Delete `Dockerfile`
  - Delete `.github/workflows/ci.yml` and `.github/workflows/build.yml` (CI/CD for the package)
  - Delete `.pre-commit-config.yaml` (hooks reference the package)
  - Delete `tests/` directory entirely (conftest.py imports `canvas_scraper`, will crash; empty test scaffold)
  - Delete `uv.lock` (lockfile for pyproject.toml, will be stale)
  - Delete `docs/` directory if empty or only contains generated docs
  - Verify deletion is safe: run `python -c "import sys; sys.path.insert(0, 'src'); import main"` after deletion
  - Verify no orphaned references: `grep -r 'canvas_scraper' src/*.py` should return no matches

  **Must NOT do**:
  - DO NOT delete anything in `src/` root (the 10 simple scripts + `__init__.py`)
  - DO NOT delete `templates/`, `data/`, `logs/`, `config.yaml`, `config.example.yaml`, `.env`, `.env.example`
  - DO NOT delete `requirements.txt`, `setup_scheduler.sh`, `setup_scheduler.ps1`, `run_with_timeout.sh`
  - DO NOT delete `QUICKSTART.md` or `README.md`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure file deletion with verification commands — no complex logic
  - **Skills**: []
    - No specialized skills needed — just bash `rm -rf` and verification

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 3, 4, 5, 6, 7, 8, 9
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `src/canvas_scraper/` — This is the entire directory to delete. Contains cli/, core/, services/, utils/ subdirectories that duplicate the simple scripts
  - `tests/conftest.py:1-36` — Contains `from canvas_scraper.core.config import Config` which will crash after deletion; delete the whole `tests/` directory

  **API/Type References**:
  - `requirements.txt` — The 7 packages here are the ONLY dependencies the simple scripts need. `pyproject.toml` adds pydantic/structlog/tenacity which are package-only

  **WHY Each Reference Matters**:
  - `src/canvas_scraper/` is zero-imported by any simple script — verified by Metis. Safe to delete entirely.
  - `tests/conftest.py` will cause immediate `ModuleNotFoundError` if left after package deletion
  - `uv.lock` is generated from pyproject.toml — becomes stale/misleading after pyproject changes

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All cruft directories and files are deleted
    Tool: Bash
    Preconditions: Repository is in current state with all files present
    Steps:
      1. Run: rm -rf src/canvas_scraper/ build/ dist/ tests/ docs/ .github/
      2. Run: rm -f build_exe.py canvas-scraper.spec Dockerfile .pre-commit-config.yaml uv.lock
      3. Run: ls src/canvas_scraper 2>&1
      4. Run: ls build dist tests .github 2>&1
    Expected Result: Steps 3 and 4 output "No such file or directory" for each path
    Failure Indicators: Any of the deleted directories still exists
    Evidence: .sisyphus/evidence/task-1-deletion-verified.txt

  Scenario: Simple scripts still import cleanly after deletion
    Tool: Bash
    Preconditions: All cruft deleted from previous scenario
    Steps:
      1. Run: python -c "import sys; sys.path.insert(0, 'src'); import main; import canvas_client; import config; import download_manager; import filter_engine; import file_organizer; import metadata_db; import course_manager; import report_generator; import email_notifier; print('ALL IMPORTS OK')"
      2. Run: grep -r 'canvas_scraper' src/*.py; echo "EXIT:$?"
    Expected Result: Step 1 prints "ALL IMPORTS OK". Step 2 shows EXIT:1 (no matches)
    Failure Indicators: ImportError, ModuleNotFoundError, or grep finding matches
    Evidence: .sisyphus/evidence/task-1-imports-verified.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-deletion-verified.txt — directory listing proving deletions
  - [ ] task-1-imports-verified.txt — import test output

  **Commit**: YES
  - Message: `refactor: delete over-engineered package layer and build artifacts`
  - Files: src/canvas_scraper/, build/, dist/, build_exe.py, canvas-scraper.spec, Dockerfile, .github/, .pre-commit-config.yaml, tests/, uv.lock, docs/
  - Pre-commit: `python -c "import sys; sys.path.insert(0, 'src'); import main; print('OK')"`

- [x] 2. Strip pyproject.toml to minimal tool config

  **What to do**:
  - Remove `[build-system]` section (hatchling build backend — no longer building a package)
  - Remove `[project]` section entirely (name, version, description, dependencies, scripts, urls, classifiers)
  - Remove `[project.optional-dependencies]` section
  - Remove `[project.scripts]` entry (`canvas-scraper = "canvas_scraper.cli:main"`)
  - Remove `[tool.hatch.build.targets.wheel]` section
  - Keep `[tool.ruff]` section as-is (useful for linting)
  - Keep `[tool.ruff.lint]`, `[tool.ruff.lint.pydocstyle]`, `[tool.ruff.lint.isort]`, `[tool.ruff.format]` as-is
  - Update `[tool.ruff.lint.isort]` — change `known-first-party = ["canvas_scraper"]` to remove it or set to empty
  - Keep `[tool.mypy]` section but remove `mypy_path = "src"` line (no longer a package)
  - Keep `[tool.pytest.ini_options]` but:
    - Change `testpaths = ["tests"]` — keep as-is
    - Remove `"--cov=canvas_scraper"` from addopts (package no longer exists)
    - Remove `"--cov-report=term-missing"`, `"--cov-report=html"`, `"--cov-report=xml"`, `"--cov-fail-under=80"` — no coverage for smoke tests
    - Keep `"--strict-markers"`, `"--strict-config"`, `"--verbose"`
  - Remove `[tool.coverage.run]`, `[tool.coverage.report]`, `[tool.coverage.html]`, `[tool.coverage.xml]` sections entirely
  - Update `src/__init__.py` version from `1.1.0` to `1.2.0`

  **Must NOT do**:
  - DO NOT delete pyproject.toml entirely — keep it as a tool config file
  - DO NOT change ruff rules or formatting config
  - DO NOT add new tool configurations

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file edit with clear section-by-section removal instructions
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 6, 7
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `pyproject.toml:1-167` — The full current file. Lines 1-3 are build-system (DELETE). Lines 5-27 are project metadata (DELETE). Lines 29-40 are dependencies (DELETE). Lines 42-53 are optional deps (DELETE). Lines 55-56 are scripts (DELETE). Lines 58-61 are URLs (DELETE). Lines 63-64 are hatch build (DELETE). Lines 66-107 are ruff (KEEP). Lines 108-124 are mypy (KEEP, update). Lines 126-145 are pytest (KEEP, update). Lines 147-167 are coverage (DELETE).

  **WHY Each Reference Matters**:
  - The `[build-system]` and `[project]` sections define a package that no longer exists — leaving them causes confusion
  - The `--cov=canvas_scraper` in pytest addopts will cause test failures since the package is deleted
  - The `known-first-party = ["canvas_scraper"]` in isort will cause false linting issues

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: pyproject.toml contains only tool config
    Tool: Bash
    Preconditions: pyproject.toml has been edited
    Steps:
      1. Run: grep -c 'build-system\|hatchling\|\[project\]\|canvas_scraper.cli' pyproject.toml; echo "EXIT:$?"
      2. Run: grep -c 'tool.ruff\|tool.mypy\|tool.pytest' pyproject.toml
      3. Run: python -m pytest --co -q 2>&1 | head -5
    Expected Result: Step 1 shows 0 matches (EXIT:1). Step 2 shows 3+ matches. Step 3 does not show coverage-related errors.
    Failure Indicators: build-system or project sections still present; ruff/mypy/pytest config missing
    Evidence: .sisyphus/evidence/task-2-pyproject-verified.txt
  ```

  **Evidence to Capture:**
  - [ ] task-2-pyproject-verified.txt — grep verification output

  **Commit**: YES
  - Message: `refactor: strip pyproject.toml to minimal tool config`
  - Files: pyproject.toml, src/__init__.py
  - Pre-commit: `grep -c 'canvas_scraper' pyproject.toml` should return 0

- [x] 3. Remove GUI setup wizard from main.py

  **What to do**:
  - Delete `src/gui_setup.py` entirely
  - In `src/main.py`:
    - Remove line 22: `from gui_setup import run_gui_setup`
    - Remove the `--cli` argument from argparse (line 802: `parser.add_argument("--cli", ...)`)
    - Simplify the setup block at lines 846-857: remove the GUI try/except, just call `setup_wizard(config)` directly
    - Simplify the auto-setup block at lines 870-881: same — remove GUI try/except, just call `setup_wizard(config)`
    - Keep `_open_native_folder_dialog()` function (lines 156-289) — it's part of the CLI wizard's optional folder browser, NOT the GUI wizard
    - Keep `_is_wsl()`, `_wsl_to_windows_path()`, `_windows_to_wsl_path()` — used by CLI wizard for WSL path handling
    - Keep the entire `setup_wizard()` function (lines 292-458) — this IS the CLI wizard

  **Must NOT do**:
  - DO NOT remove `_open_native_folder_dialog()` — it's used by the CLI wizard for an optional folder browser
  - DO NOT remove `_is_wsl()` or the WSL path conversion functions — they're used by setup_wizard AND scheduling
  - DO NOT modify the `setup_wizard()` function itself
  - DO NOT modify `run_sync()` or any sync logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file deletion + targeted line edits in main.py
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 6, 8, 9
  - **Blocked By**: Task 1 (gui_setup.py references canvas_scraper indirectly via config — verify after package deletion)

  **References**:

  **Pattern References**:
  - `src/main.py:22` — `from gui_setup import run_gui_setup` — DELETE this import
  - `src/main.py:802` — `parser.add_argument("--cli", ...)` — DELETE this argument
  - `src/main.py:846-857` — First GUI try/except block: `if not getattr(args, "cli", False) and (os.environ.get("DISPLAY") or os.name == "nt"): run_gui_setup(config)` — REPLACE with just `setup_wizard(config)`
  - `src/main.py:870-881` — Second GUI try/except block (same pattern) — REPLACE with just `setup_wizard(config)`
  - `src/gui_setup.py` — The 203-line tkinter GUI wizard file to DELETE entirely

  **WHY Each Reference Matters**:
  - Line 22 import will cause `ModuleNotFoundError` after gui_setup.py is deleted
  - Lines 846-857 and 870-881 call `run_gui_setup()` which no longer exists — must fall through to `setup_wizard()`
  - The `--cli` flag becomes meaningless when GUI is removed (CLI is the only mode)

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: GUI wizard removed, CLI wizard intact
    Tool: Bash
    Preconditions: gui_setup.py deleted, main.py edited
    Steps:
      1. Run: test ! -f src/gui_setup.py && echo "GUI DELETED"
      2. Run: grep -c 'gui_setup\|run_gui_setup\|SetupGUI' src/main.py; echo "EXIT:$?"
      3. Run: grep -c 'setup_wizard' src/main.py
      4. Run: python -c "import sys; sys.path.insert(0, 'src'; import main; print('IMPORT OK')"
    Expected Result: Step 1 prints "GUI DELETED". Step 2 shows 0 (EXIT:1). Step 3 shows 2+ matches (setup_wizard still exists). Step 4 prints "IMPORT OK".
    Failure Indicators: gui_setup.py still exists, or references remain, or import fails
    Evidence: .sisyphus/evidence/task-3-gui-removed.txt

  Scenario: --cli flag removed from argparse
    Tool: Bash
    Preconditions: main.py has been edited
    Steps:
      1. Run: python -c "import sys; sys.path.insert(0, 'src'); from main import main; import argparse" (should not error)
      2. Run: grep -c '\-\-cli' src/main.py; echo "EXIT:$?"
    Expected Result: Step 2 shows 0 (EXIT:1) — no --cli flag references
    Failure Indicators: --cli flag still in argparse
    Evidence: .sisyphus/evidence/task-3-cli-flag-removed.txt
  ```

  **Evidence to Capture:**
  - [ ] task-3-gui-removed.txt — deletion and reference verification
  - [ ] task-3-cli-flag-removed.txt — argparse verification

  **Commit**: YES
  - Message: `refactor: remove GUI setup wizard, keep CLI-only`
  - Files: src/gui_setup.py (deleted), src/main.py (edited)
  - Pre-commit: `python -c "import sys; sys.path.insert(0, 'src'); import main; print('OK')"`

- [x] 4. Fix run_with_timeout.sh venv detection

  **What to do**:
  - The script hardcodes `./venv/bin/python` (line 13) but the repo also has a `.venv/` directory
  - Add venv auto-detection: check for `./venv/bin/python` first, then `./.venv/bin/python`, then fall back to system `python3`
  - Add a clear error message if no Python is found
  - Add a log header with timestamp so scheduled runs are distinguishable in the log file
  - Keep the `timeout --signal=TERM --kill-after=30 900` wrapper (it works correctly)

  **Must NOT do**:
  - DO NOT change the timeout values or signal handling
  - DO NOT add complex logic — this should remain a simple wrapper script
  - DO NOT change the log redirect behavior (stdout+stderr to logs/scraper.log)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small bash script edit — add 5-10 lines of venv detection
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7)
  - **Blocks**: Task 5, 9
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `run_with_timeout.sh:1-13` — The entire current script. Line 13 is the hardcoded `./venv/bin/python` path
  - `.venv/` directory exists in project root alongside `venv/` — need to handle both

  **WHY Each Reference Matters**:
  - If the wrong venv path is used, Python isn't found, the script silently exits 127, and no logs are written — this is likely the root cause of "doesn't work"

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Script detects correct Python interpreter
    Tool: Bash
    Preconditions: run_with_timeout.sh has been edited
    Steps:
      1. Run: bash -n run_with_timeout.sh (syntax check)
      2. Run: grep -c 'venv.*python\|\.venv.*python' run_with_timeout.sh
      3. Run: head -20 run_with_timeout.sh
    Expected Result: Step 1 exits 0 (valid syntax). Step 2 shows 2+ matches (checks both venv paths). Step 3 shows auto-detection logic.
    Failure Indicators: Syntax error, or only one venv path checked
    Evidence: .sisyphus/evidence/task-4-timeout-script.txt

  Scenario: Error handling when no Python found
    Tool: Bash
    Preconditions: run_with_timeout.sh updated
    Steps:
      1. Run: grep -c 'not found\|No Python\|error\|exit 1' run_with_timeout.sh
    Expected Result: At least 1 match — script has a fallback error message
    Failure Indicators: No error handling for missing Python
    Evidence: .sisyphus/evidence/task-4-error-handling.txt
  ```

  **Evidence to Capture:**
  - [ ] task-4-timeout-script.txt — updated script content and syntax check
  - [ ] task-4-error-handling.txt — error path verification

  **Commit**: YES (groups with Task 5)
  - Message: `fix: WSL scheduling — proper distro detection, path handling, output redirection`
  - Files: run_with_timeout.sh, setup_scheduler.ps1
  - Pre-commit: `bash -n run_with_timeout.sh`

- [x] 5. Fix WSL scheduling in setup_scheduler.ps1

  **What to do**:
  This is the main bug fix. The PowerShell script creates a Windows Task Scheduler task that invokes the scraper via WSL, but it "doesn't hang but doesn't work." Multiple issues identified by Metis:

  **Issue 1: No `--distribution` flag**
  - Current: `wsl.exe -u $WslUsername -- bash -c "..."` doesn't specify which WSL distro
  - Fix: Auto-detect the default distro at setup time: `$distro = (wsl --list --quiet | Select-Object -First 1).Trim()`
  - Use it: `wsl.exe --distribution $distro -u $WslUsername -- bash -c "..."`

  **Issue 2: Unreliable `wsl pwd` for path detection**
  - Current: Line 98 uses `wsl pwd` which only works from an active WSL terminal session
  - Fix: The script already HAS `Get-WSLProjectPath` function (line 51) that converts Windows paths to WSL paths!
  - Replace lines 98-108 with: `$WslProjectPath = Get-WSLProjectPath $ScriptDir`
  - If `$ScriptDir` starts with `\\wsl$` or `\\wsl.localhost`, extract the WSL path directly

  **Issue 3: No output redirection at outer bash level**
  - Current: `run_with_timeout.sh` redirects internally, but `bash -c` itself can output to stdout/stderr
  - Fix: Wrap entire command: `bash -c "exec >> /path/logs/scraper.log 2>&1; bash run_with_timeout.sh"`

  **Issue 4: Better diagnostic output for -RunNow**
  - Add: When `-RunNow` is called, print the exact registered command before starting the task so user can debug

  **Must NOT do**:
  - DO NOT change the trigger types (login, startup, daily) — they work correctly
  - DO NOT change the Task Scheduler principal or settings (they're correct)
  - DO NOT change `setup_scheduler.sh` (the bash wrapper for Mac/Linux/WSL)
  - DO NOT change the signal handling in main.py

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: PowerShell debugging with WSL path conversion, multiple interacting issues, needs careful testing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6, 7)
  - **Blocks**: Tasks 8, 9
  - **Blocked By**: Task 4 (run_with_timeout.sh must be fixed first since PS1 invokes it)

  **References**:

  **Pattern References**:
  - `setup_scheduler.ps1:37-67` — Helper functions: `Test-IsWSL`, `Get-WSLUsername`, `Get-WSLProjectPath`. The path conversion function already exists but isn't being used for WSL path detection!
  - `setup_scheduler.ps1:81-122` — WSL detection and command building. Line 98 uses the unreliable `wsl pwd`. Line 116-119 builds the wsl.exe command without `--distribution`.
  - `setup_scheduler.ps1:144-162` — Trigger configuration (KEEP AS-IS)
  - `setup_scheduler.ps1:164-171` — Task Scheduler settings (KEEP AS-IS)
  - `run_with_timeout.sh:1-13` — The wrapper script that PS1 invokes via WSL

  **External References**:
  - WSL CLI docs: `wsl --distribution <distro>` flag pins which distro to use
  - Known issue: `wsl pwd` is unreliable from non-interactive contexts (GitHub WSL issues #8585)

  **WHY Each Reference Matters**:
  - Line 98 (`wsl pwd`) is likely THE root cause — when Task Scheduler runs the PS1 at setup time from a WSL terminal, `wsl pwd` works, but the path may be wrong or the function at line 51 should be used instead
  - Lines 116-119 build the task command — missing `--distribution` means wrong distro could be selected
  - The `Get-WSLProjectPath` function (line 51) is the CORRECT way to detect the path but isn't being used

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: PowerShell script has valid syntax and uses --distribution flag
    Tool: Bash
    Preconditions: setup_scheduler.ps1 has been edited
    Steps:
      1. Run: grep -c '\-\-distribution' setup_scheduler.ps1
      2. Run: grep -c 'wsl pwd' setup_scheduler.ps1
      3. Run: grep -c 'Get-WSLProjectPath' setup_scheduler.ps1
    Expected Result: Step 1 shows 1+ (distribution flag present). Step 2 shows 0 (wsl pwd removed). Step 3 shows 2+ (function defined AND called).
    Failure Indicators: Missing --distribution, wsl pwd still used, Get-WSLProjectPath not called for path detection
    Evidence: .sisyphus/evidence/task-5-ps1-fixes.txt

  Scenario: RunNow shows diagnostic output
    Tool: Bash
    Preconditions: setup_scheduler.ps1 has been edited
    Steps:
      1. Run: grep -A5 'RunNow' setup_scheduler.ps1 | grep -ic 'command\|execute\|action\|registered'
    Expected Result: At least 1 match — RunNow section prints diagnostic info about what will run
    Failure Indicators: RunNow section has no diagnostic output
    Evidence: .sisyphus/evidence/task-5-runnow-diagnostic.txt

  Scenario: Outer output redirection in WSL command
    Tool: Bash
    Preconditions: setup_scheduler.ps1 has been edited
    Steps:
      1. Run: grep 'exec >>' setup_scheduler.ps1
    Expected Result: At least 1 match — outer bash -c redirects all output to log file
    Failure Indicators: No exec redirect in the WSL command string
    Evidence: .sisyphus/evidence/task-5-output-redirect.txt
  ```

  **Evidence to Capture:**
  - [ ] task-5-ps1-fixes.txt — grep verification of all fixes
  - [ ] task-5-runnow-diagnostic.txt — RunNow diagnostic verification
  - [ ] task-5-output-redirect.txt — output redirection verification

  **Commit**: YES (groups with Task 4)
  - Message: `fix: WSL scheduling — proper distro detection, path handling, output redirection`
  - Files: setup_scheduler.ps1
  - Pre-commit: `grep -c 'wsl pwd' setup_scheduler.ps1` should return 0

- [x] 6. Write smoke tests

  **What to do**:
  Create a basic test suite with mocks for the critical paths:

  - Create `tests/__init__.py` (empty)
  - Create `tests/conftest.py` with:
    - `sys.path.insert(0, 'src')` so tests can import the simple scripts
    - Shared fixtures: mock config object, mock Canvas client, mock SMTP connection
  - Create `tests/test_imports.py`:
    - Test that ALL 10 src/*.py modules import without error
    - This catches any broken cross-references after cleanup
  - Create `tests/test_config.py`:
    - Test Config loads from `config.example.yaml` + mock env vars
    - Test Config validates required fields
  - Create `tests/test_canvas_client.py`:
    - Test CanvasClient constructor (mock canvasapi.Canvas)
    - Test `test_connection()` returns (True, message) on success (mock get_current_user)
    - Test `test_connection()` returns (False, message) on failure
  - Create `tests/test_email.py`:
    - Test EmailNotifier constructor (mock config)
    - Test `test_connection()` with mocked SMTP (success + failure)
  - Create `tests/test_filters.py`:
    - Test FilterEngine with extension blacklist (no mocks needed — pure logic)
    - Test FilterEngine with size limits
    - Test FilterEngine with name patterns

  **Must NOT do**:
  - DO NOT write integration tests requiring real Canvas API or email credentials
  - DO NOT add pytest-cov or coverage thresholds
  - DO NOT test download_manager, report_generator, or metadata_db (scope creep)
  - DO NOT use real API tokens or email passwords in test code
  - DO NOT import from `canvas_scraper` package (it's deleted)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple test files with mocking patterns — needs understanding of the codebase to write correct mocks
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 7)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 1, 2, 3 (needs package deleted, pyproject updated, main.py cleaned)

  **References**:

  **Pattern References**:
  - `src/config.py` — The Config class that loads config.yaml + .env. Tests need to mock env vars and provide config.example.yaml
  - `src/canvas_client.py:16-44` — CanvasClient class with `__init__` and `test_connection()`. Mock `canvasapi.Canvas` and `canvas.get_current_user()`
  - `src/email_notifier.py:16-50` — EmailNotifier class with `__init__` and `test_connection()`. Mock `smtplib.SMTP`
  - `src/filter_engine.py` — FilterEngine class with `should_download()` method. Pure logic — no mocks needed, test with sample file metadata dicts
  - `config.example.yaml` — Example config file that tests can load
  - `requirements.txt` — No pytest-cov or coverage dependencies — keep it simple

  **WHY Each Reference Matters**:
  - Config is the foundation — if it breaks, nothing works. Test it first.
  - CanvasClient.test_connection() is called by the setup wizard — mock Canvas to avoid real API calls
  - EmailNotifier.test_connection() verifies email creds — mock SMTP to avoid real sends
  - FilterEngine is pure logic with no side effects — easiest to test, high value

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All smoke tests pass
    Tool: Bash
    Preconditions: All test files created, dependencies installed
    Steps:
      1. Run: python -m pytest tests/ -v
    Expected Result: Exit code 0, all tests pass, output shows test names and PASSED for each
    Failure Indicators: Any test FAILED, ImportError, ModuleNotFoundError
    Evidence: .sisyphus/evidence/task-6-test-results.txt

  Scenario: Tests use mocks, not real credentials
    Tool: Bash
    Preconditions: Test files exist
    Steps:
      1. Run: grep -r 'CANVAS_API_TOKEN\|EMAIL_APP_PASSWORD' tests/ --include='*.py' | grep -v 'mock\|Mock\|patch\|fixture\|example\|env.example\|monkeypatch'
    Expected Result: Exit code 1 (no real credential usage found)
    Failure Indicators: Hardcoded real credentials in tests
    Evidence: .sisyphus/evidence/task-6-no-real-creds.txt
  ```

  **Evidence to Capture:**
  - [ ] task-6-test-results.txt — full pytest output
  - [ ] task-6-no-real-creds.txt — credential verification

  **Commit**: YES
  - Message: `test: add smoke tests with mocks for config, canvas, email, filters`
  - Files: tests/__init__.py, tests/conftest.py, tests/test_imports.py, tests/test_config.py, tests/test_canvas_client.py, tests/test_email.py, tests/test_filters.py
  - Pre-commit: `python -m pytest tests/ -v`

- [x] 7. Update .gitignore and clean tracked build artifacts

  **What to do**:
  - Review `.gitignore` and ensure it covers:
    - `build/`, `dist/`, `*.spec` (PyInstaller artifacts — prevent re-creation)
    - `.ruff_cache/` (already in .gitignore? verify)
    - `__pycache__/`, `*.pyc` (standard Python)
    - `htmlcov/`, `coverage.xml`, `.coverage` (coverage artifacts)
    - `.venv/`, `venv/` (virtual environments)
    - `data/scraper.db` (runtime database)
    - `logs/` (runtime logs)
    - `.env` (secrets)
  - Remove `.ruff_cache/` from git tracking if currently tracked: `git rm -r --cached .ruff_cache/`
  - Verify no secrets or build artifacts are tracked

  **Must NOT do**:
  - DO NOT remove config.yaml from gitignore (it contains user-specific settings)
  - DO NOT add config.example.yaml to gitignore (it's a template)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple .gitignore review and cleanup
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `.gitignore` — Current gitignore file, review for completeness
  - `.ruff_cache/` — Directory that may be tracked in git (should be ignored)

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: .gitignore covers all necessary patterns
    Tool: Bash
    Preconditions: .gitignore has been updated
    Steps:
      1. Run: grep -c 'build/\|dist/\|__pycache__\|\.env$\|venv\|scraper\.db\|logs/' .gitignore
      2. Run: git status --porcelain | grep -c '.ruff_cache'
    Expected Result: Step 1 shows 5+ matches. Step 2 shows 0 (ruff_cache not tracked).
    Failure Indicators: Missing critical .gitignore patterns
    Evidence: .sisyphus/evidence/task-7-gitignore.txt
  ```

  **Evidence to Capture:**
  - [ ] task-7-gitignore.txt — gitignore content verification

  **Commit**: YES
  - Message: `chore: update gitignore, clean tracked artifacts`
  - Files: .gitignore
  - Pre-commit: None

- [x] 8. Update README.md and QUICKSTART.md

  **What to do**:
  - In `README.md`:
    - Remove the "Standalone Executable (For Non-Technical Users)" section entirely (build_exe.py is deleted)
    - Remove the "Developer: Building the Executable" section entirely
    - Remove "GUI Setup" and "GUI Setup Wizard" references — describe CLI setup wizard only
    - Remove "New in v1.1.0" section (outdated, this is now v1.2.0)
    - Update version references to `1.2.0`
    - Remove any references to `canvas_scraper` package, `pip install -e .`, or `canvas-scraper` CLI command
    - Remove Dockerfile references
    - Keep: installation instructions (git clone, venv, pip install -r requirements.txt)
    - Keep: setup wizard instructions (`python src/main.py --setup`)
    - Keep: configuration section, scheduling section, troubleshooting section, file organization example
    - Update WSL troubleshooting if the scheduling fix changes any behavior
  - In `QUICKSTART.md`:
    - Remove GUI references if any exist
    - Update to match simplified project

  **Must NOT do**:
  - DO NOT rewrite the entire README — only update sections affected by deletions
  - DO NOT add new sections (architecture docs, API docs, contributing guide)
  - DO NOT add emojis or change the writing style
  - DO NOT remove the WSL troubleshooting section

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Targeted section removal/update in markdown files
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 9)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 1, 3, 5 (needs to know what was deleted and what WSL fix looks like)

  **References**:

  **Pattern References**:
  - `README.md` — Full README, ~300 lines. Sections to remove are clearly labeled ("Standalone Executable", "Building the Executable", "GUI Setup")
  - `QUICKSTART.md` — Quick start guide, review for GUI references

  **WHY Each Reference Matters**:
  - README references deleted files (build_exe.py, gui_setup.py, Dockerfile) — readers will be confused
  - Version references (v1.1.0) are outdated

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: No references to deleted artifacts in docs
    Tool: Bash
    Preconditions: README.md and QUICKSTART.md updated
    Steps:
      1. Run: grep -ic 'build_exe\|canvas_scraper\|gui_setup\|Dockerfile\|PyInstaller\|GUI Setup Wizard\|v1\.1\.0' README.md
      2. Run: grep -ic 'build_exe\|canvas_scraper\|gui_setup\|Dockerfile\|PyInstaller' QUICKSTART.md
      3. Run: grep -c '1\.2\.0' README.md
    Expected Result: Steps 1 and 2 show 0 (no stale references). Step 3 shows 1+ (version updated).
    Failure Indicators: Stale references to deleted artifacts, or version not updated
    Evidence: .sisyphus/evidence/task-8-docs-verified.txt
  ```

  **Evidence to Capture:**
  - [ ] task-8-docs-verified.txt — grep verification of cleaned docs

  **Commit**: YES
  - Message: `docs: update README and QUICKSTART for simplified project`
  - Files: README.md, QUICKSTART.md
  - Pre-commit: None

- [x] 9. Final integration verification

  **What to do**:
  - This is the integration gate — verify everything works together after all tasks complete:
  - Run ALL import checks: every `src/*.py` module imports cleanly
  - Run `python src/main.py --help` — verify argparse works, no --cli flag, no GUI references
  - Run `python -m pytest tests/ -v` — all smoke tests pass
  - Verify file structure: only expected files remain (no orphaned build/package artifacts)
  - Verify `config.example.yaml` is valid and loadable
  - Verify `templates/email_report.html` exists and is referenced correctly
  - Run `python src/main.py --dry-run` — may fail on missing config/credentials, but should NOT fail on import errors
  - Check git status: no untracked files that should be gitignored, no accidentally staged secrets
  - Produce a final summary report

  **Must NOT do**:
  - DO NOT run with real Canvas credentials
  - DO NOT send real emails
  - DO NOT register a real Task Scheduler task
  - DO NOT make any code changes — this is verification only

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Comprehensive verification across all modified files — needs to understand the full picture
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (runs after Task 8)
  - **Blocks**: F1-F4
  - **Blocked By**: ALL tasks 1-8

  **References**:

  **Pattern References**:
  - All `src/*.py` files — verify imports
  - `tests/` directory — verify test suite
  - `pyproject.toml` — verify tool config works
  - `README.md`, `QUICKSTART.md` — verify no stale references
  - `.gitignore` — verify cleanup
  - `config.example.yaml` — verify loadable
  - `templates/email_report.html` — verify exists

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full integration check
    Tool: Bash
    Preconditions: All tasks 1-8 complete
    Steps:
      1. Run: python -c "import sys; sys.path.insert(0, 'src'); import main; import canvas_client; import config; import download_manager; import filter_engine; import file_organizer; import metadata_db; import course_manager; import report_generator; import email_notifier; print('ALL IMPORTS OK')"
      2. Run: python src/main.py --help 2>&1 | head -3
      3. Run: python -m pytest tests/ -v 2>&1 | tail -5
      4. Run: ls templates/email_report.html config.example.yaml requirements.txt
      5. Run: test ! -d src/canvas_scraper && test ! -d build && test ! -d dist && test ! -f Dockerfile && echo "CLEAN"
    Expected Result: Step 1 prints "ALL IMPORTS OK". Step 2 shows help text. Step 3 shows all tests passed. Step 4 lists all 3 files. Step 5 prints "CLEAN".
    Failure Indicators: Any import error, missing file, failed test, or stale artifact
    Evidence: .sisyphus/evidence/task-9-integration.txt

  Scenario: No orphaned references across entire project
    Tool: Bash
    Preconditions: All tasks complete
    Steps:
      1. Run: grep -r 'canvas_scraper' src/*.py README.md QUICKSTART.md pyproject.toml 2>/dev/null; echo "EXIT:$?"
      2. Run: grep -r 'gui_setup\|run_gui_setup' src/*.py README.md 2>/dev/null; echo "EXIT:$?"
      3. Run: grep -r 'build_exe\|PyInstaller' src/*.py README.md 2>/dev/null; echo "EXIT:$?"
    Expected Result: All three show EXIT:1 (no matches)
    Failure Indicators: Any grep match found
    Evidence: .sisyphus/evidence/task-9-no-orphans.txt
  ```

  **Evidence to Capture:**
  - [ ] task-9-integration.txt — full integration check output
  - [ ] task-9-no-orphans.txt — orphaned reference check

  **Commit**: NO (verification only — no file changes)


## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection -> fix -> re-run.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (check file exists, run import, read content). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m pytest tests/ -v`. Review all changed files for: unused imports, broken references to deleted modules, hardcoded paths that no longer exist, console.log/print statements that reference removed features. Check for orphaned references to `canvas_scraper`, `gui_setup`, `build_exe`.
  Output: `Tests [N pass/N fail] | Orphan Refs [N found] | VERDICT`

- [x] F3. **Import and Runtime QA** — `unspecified-high`
  Start from clean state. Import every module in `src/`. Run `python src/main.py --help` to verify argparse works. Run `python src/main.py --dry-run` (will fail on config, but should not have import errors). Verify `python src/main.py --setup --cli` starts the setup wizard prompts (don't complete it). Check all file references in README.md point to files that exist.
  Output: `Imports [N/N pass] | CLI [PASS/FAIL] | Docs Refs [N/N valid] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance: no core logic was modified, no script consolidation happened, no new features added. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Scope Creep [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

| Task | Commit Message | Files |
|------|---------------|-------|
| 1 | `refactor: delete over-engineered package layer and build artifacts` | src/canvas_scraper/, build/, dist/, build_exe.py, canvas-scraper.spec, Dockerfile, .github/, .pre-commit-config.yaml, tests/, uv.lock |
| 2 | `refactor: strip pyproject.toml to minimal tool config` | pyproject.toml |
| 3 | `refactor: remove GUI setup wizard, keep CLI-only` | src/gui_setup.py, src/main.py |
| 4+5 | `fix: WSL scheduling — proper distro detection, path handling, output redirection` | run_with_timeout.sh, setup_scheduler.ps1 |
| 6 | `test: add smoke tests with mocks for config, canvas, email, filters` | tests/ |
| 7 | `chore: update gitignore, clean tracked artifacts` | .gitignore |
| 8 | `docs: update README and QUICKSTART for simplified project` | README.md, QUICKSTART.md |

---

## Success Criteria

### Verification Commands
```bash
# All imports work
python -c "import sys; sys.path.insert(0, 'src'); import main; import canvas_client; import config; import download_manager; import filter_engine; import file_organizer; import metadata_db; import course_manager; import report_generator; import email_notifier; print('OK')"
# Expected: OK

# No deleted module references
grep -r "canvas_scraper\|gui_setup\|build_exe" src/*.py
# Expected: exit code 1 (no matches)

# Tests pass
python -m pytest tests/ -v
# Expected: exit code 0

# CLI works
python src/main.py --help
# Expected: shows help text without errors

# Deleted dirs gone
ls src/canvas_scraper build dist 2>&1
# Expected: "No such file or directory" for all three
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All smoke tests pass
- [x] README accurate to current state
- [x] WSL scheduling instructions provided (user verifies on Windows)
