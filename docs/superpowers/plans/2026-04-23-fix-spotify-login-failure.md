# Spotify Login Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the crash and session mismatch causing Spotify login failures.

**Architecture:** Robust token handling in the Social Account Adapter and correct Site configuration in the database.

**Tech Stack:** Django, django-allauth, PostgreSQL.

---

### Task 1: Fix NoneType Error in MoodsicSocialAccountAdapter

**Files:**
- Modify: `apps/users/adapter.py`

- [ ] **Step 1: Implement defensive checks for tokens**
Add null checks before accessing `token_data.token_secret` and improve logging.

```python
<<<<
            # --- LOGS DE TOKENS (Lo que pediste ver) ---
            if token_data:
                # Mostramos los primeros 40 caracteres para confirmar que es un token real
                print(f"--- [TOKEN ACCESS]: {token_data.token[:40]}... ---")
                print(f"--- [TOKEN REFRESH]: {token_data.token_secret[:20]}... ---")
                print(f"--- [TOKEN EXPIRES]: {token_data.expires_at} ---")
            else:
                print("--- ⚠️ WARNING: Spotify NO envió token_data ---")
====
            # --- LOGS DE TOKENS ---
            if token_data:
                access_token_preview = token_data.token[:40] if token_data.token else "None"
                refresh_token_preview = token_data.token_secret[:20] if token_data.token_secret else "None"
                print(f"--- [TOKEN ACCESS]: {access_token_preview}... ---")
                print(f"--- [TOKEN REFRESH]: {refresh_token_preview}... ---")
                print(f"--- [TOKEN EXPIRES]: {token_data.expires_at} ---")
            else:
                print("--- ⚠️ WARNING: Spotify NO envió token_data ---")
>>>>
```

- [ ] **Step 2: Commit**

```bash
git add apps/users/adapter.py
git commit -m "fix: add defensive checks to social adapter logging"
```

### Task 2: Verify Site Configuration

**Files:**
- Database change (Site table)

- [ ] **Step 1: Ensure Site record is correct**
Verify that the `Site` object with `id=1` has `domain='127.0.0.1:8000'`. (Already updated in design phase, but good to double check).

Run: `uv run python manage.py shell -c "from django.contrib.sites.models import Site; print(Site.objects.get(id=1).domain)"`

### Task 3: Final Verification

- [ ] **Step 1: Run project tests**
Run: `uv run pytest apps/users/tests/test_adapter.py`
Expected: PASS

- [ ] **Step 2: Manual Verification instruction**
The user should restart the server and try to login from `http://127.0.0.1:8000/accounts/spotify/login/`.
