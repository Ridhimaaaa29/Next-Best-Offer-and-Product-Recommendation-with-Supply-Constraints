# Engineering Challenge Resolution Log

## Challenge 01: Missing Python Dependencies

**Issue:** The project's virtual environment contained only pip. FastAPI and other application dependencies were unavailable, causing application imports to fail.

**Root Cause:** The virtual environment had been created but project requirements had not been installed.

**Resolution:**
- Verified Python 3.14.6.
- Redirected temporary installation files and pip cache to the F drive.
- Installed dependencies using `requirements.txt`.
- Verified dependencies using `pip check`.
- Verified core application imports.

**Validation:** `No broken requirements found` and `Application import successful`.

**Status:** Resolved.

## Challenge 02: Backend Runtime Verification

**Issue:** Backend startup and database/model availability had not been verified.

**Resolution:**
- Started the FastAPI application using Uvicorn.
- Tested `/health`, `/docs`, and `/api/v1/health`.

**Validation:**
- All three endpoints returned HTTP 200.
- Health response confirmed database connectivity.
- Gradient Boosting model was loaded successfully.

**Status:** Resolved.

## Challenge 03: Test Execution and Deprecation Warnings

**Issue:** The project test suite needed execution verification. During execution, Starlette emitted three deprecation warnings.

**Resolution:**
- Successfully collected 29 tests.
- Executed the complete test suite using the selected virtual environment.

**Validation:**
- 29 tests passed.
- 0 tests failed.
- Execution time: 461.85 seconds.
- 3 deprecation warnings remain.

**Status:** Tests passed; warning investigation pending.

**Next Action:** Investigate the Starlette/httpx TestClient compatibility warning and deprecated HTTP 422 constant. Apply only necessary changes and rerun the affected tests.

### Challenge: HTTP 422 Deprecation Warnings

**Status:** Resolved

**Problem:**
The test suite reported two deprecation warnings because the application used `status.HTTP_422_UNPROCESSABLE_ENTITY` in the validation exception handler.

**Root Cause:**
The installed Starlette version recommends `HTTP_422_UNPROCESSABLE_CONTENT` instead of the deprecated constant.

**Solution:**
Updated `backend/app/middleware/error_handler.py` by replacing:

`status.HTTP_422_UNPROCESSABLE_ENTITY`

with:

`status.HTTP_422_UNPROCESSABLE_CONTENT`

No dependency upgrades or changes to exception-handling behaviour were required.

**Validation:**
Executed:

`.\.venv\Scripts\python.exe -m pytest tests/api/test_recommend.py -q`

Result: **6 passed, 0 failed, 1 warning.**

The two HTTP 422 deprecation warnings disappeared. One third-party Starlette/HTTPX deprecation warning remains and is documented for future dependency migration.

**Evidence:**
- Original test output showing three warnings.
- Updated code showing the replacement constant.
- Targeted test output showing six passing tests and one remaining warning.

### Full Regression Test – 05 November 2026

**Status:** Passed

**Command executed:**
`.\.venv\Scripts\python.exe -m pytest -q --tb=short`

**Results:**
- Total tests: 29
- Passed: 29
- Failed: 0
- Warnings: 1
- Execution time: 432.57 seconds

**Verification:**
The full test suite passed after replacing the deprecated HTTP 422 status constant in the centralized error handler.

The two application-generated HTTP 422 deprecation warnings are no longer present.

One third-party Starlette/HTTPX deprecation warning remains. No dependency changes were made.

**Conclusion:**
The error-handler change passed both targeted API tests (6 passed) and the complete regression suite (29 passed).