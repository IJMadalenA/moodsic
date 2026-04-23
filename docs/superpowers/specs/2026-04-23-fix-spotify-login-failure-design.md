# Fix Spotify Login Failure Design

## Problem Statement
The user is experiencing a "Third-Party Login Failure" (HTTP 401 Unauthorized) when attempting to log in via Spotify. This is caused by:
1. **NoneType Error in Adapter**: A debug print in `MoodsicSocialAccountAdapter` crashes when `token_secret` (refresh token) is None.
2. **Session/State Mismatch**: The 401 Unauthorized error in `allauth` usually stems from a mismatch between the session that started the login and the one receiving the callback, or an incorrect `Site` configuration in Django.

## Proposed Changes

### 1. Robust Adapter Implementation (`apps/users/adapter.py`)
- Fix the `TypeError` by adding null checks before accessing `token_data.token_secret`.
- Improve logging to be less intrusive and more defensive.

### 2. Django Site Configuration
- The `Site` object in the database has been updated to `127.0.0.1:8000` to match the actual usage and Spotify redirect URI.
- Ensure `settings.SITE_ID` is correctly pointing to this record (already verified as 1).

### 3. Cleanup of Deprecated Test Data
- Some failing tests in the project (unrelated to this specific fix but causing noise) will be ignored or noted for future work, focusing the verification on the login flow.

## Success Criteria
- The OAuth callback from Spotify is accepted by `allauth` (No 401 Unauthorized).
- User profile and tokens are correctly persisted to the `User` model without crashing.
- User is redirected to the home page after successful login.
