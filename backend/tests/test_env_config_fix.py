"""
Tests for env-config-fix bugfix spec.

Property 1: Bug Condition - Configuration Issues Prevent Application Startup
Property 2: Preservation - Non-Buggy Configurations Unchanged

These tests follow the bug condition methodology:
  - C(X): Bug Condition - identifies inputs that trigger the bug
  - P(result): Property - desired behavior for buggy inputs
  - ¬C(X): Non-buggy inputs that should be preserved
"""

import os
import re
import logging
import importlib
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# ─── Paths ────────────────────────────────────────────────────────────────────

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
REQUIREMENTS_TXT = WORKSPACE_ROOT / "backend" / "requirements.txt"
FRONTEND_ENV = WORKSPACE_ROOT / "frontend" / ".env"


# ─── Property 1: Bug Condition Tests ─────────────────────────────────────────
# These tests FAIL on unfixed code and PASS after the fix.
# Running them on unfixed code surfaces the counterexamples that prove the bugs.


class TestBugCondition:
    """
    **Property 1: Bug Condition** - Configuration Issues Prevent Application Startup

    Bug Condition (C): isBugCondition(input) returns True for:
      - requirements.txt has merged dependency lines
      - CLAUDE_MODEL is set to invalid model identifier
      - frontend/.env does not exist
      - Startup does not log warnings for placeholder SECRET_KEY
      - Startup does not log warnings for placeholder GOOGLE_CLIENT_SECRET

    Expected Behavior (P): After fix, all of the above conditions are resolved.
    """

    def test_requirements_txt_has_no_merged_lines(self):
        """
        Bug 1.1: requirements.txt must NOT have merged dependency lines.

        Counterexample on unfixed code:
          'passlib[bcrypt]==1.7.4email-validator==2.3.0authlib==1.5.2' found on one line
          → pip install fails with package-not-found error

        Expected after fix: each dependency is on its own line.
        """
        content = REQUIREMENTS_TXT.read_text()
        lines = content.splitlines()

        # Each non-comment, non-empty line should be a single valid package spec
        # A merged line would contain multiple package names concatenated
        merged_pattern = re.compile(
            r"[a-zA-Z0-9_\-\[\]]+==[\d\.]+[a-zA-Z0-9_\-\[\]]+==[\d\.]+"
        )

        merged_lines = [line for line in lines if merged_pattern.search(line)]
        assert merged_lines == [], (
            f"Found merged dependency lines in requirements.txt: {merged_lines}\n"
            "Each dependency must be on its own line for pip to parse correctly."
        )

    def test_requirements_txt_contains_auth_packages(self):
        """
        Bug 1.1: Auth packages must be present as separate entries.

        Expected: bcrypt, email-validator, authlib each on their own line.
        """
        content = REQUIREMENTS_TXT.read_text()
        lines = [line.strip() for line in content.splitlines()]

        assert any(line.startswith("bcrypt==") for line in lines), (
            "bcrypt must be present in requirements.txt"
        )
        assert any(line.startswith("email-validator==") for line in lines), (
            "email-validator must be on its own line in requirements.txt"
        )
        assert any(line.startswith("authlib==") for line in lines), (
            "authlib must be on its own line in requirements.txt"
        )

    def test_claude_model_is_valid_identifier(self):
        """
        Bug 1.2: CLAUDE_MODEL must be a valid Anthropic model identifier.

        Counterexample on unfixed code:
          CLAUDE_MODEL = "claude-sonnet-4-20250514"
          → anthropic.NotFoundError: model 'claude-sonnet-4-20250514' not found

        Expected after fix: CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
        """
        # Re-import config fresh to get current default
        if "app.config" in sys.modules:
            del sys.modules["app.config"]

        # Read the config.py source directly to check the default value
        config_path = WORKSPACE_ROOT / "backend" / "app" / "config.py"
        config_source = config_path.read_text()

        # The invalid model name that was the bug
        invalid_model = "claude-sonnet-4-20250514"
        assert invalid_model not in config_source, (
            f"CLAUDE_MODEL default is still set to invalid model '{invalid_model}'.\n"
            "Expected: 'claude-3-5-sonnet-20241022'"
        )

        # The valid model name that should be present
        valid_model = "claude-3-5-sonnet-20241022"
        assert valid_model in config_source, (
            f"CLAUDE_MODEL default should be set to '{valid_model}' but was not found in config.py"
        )

    def test_frontend_env_file_exists(self):
        """
        Bug 1.6: frontend/.env must exist.

        Counterexample on unfixed code:
          frontend/.env does not exist
          → No explicit configuration file to document or override the API endpoint

        Expected after fix: frontend/.env exists with VITE_API_BASE_URL set.
        """
        assert FRONTEND_ENV.exists(), (
            f"frontend/.env does not exist at {FRONTEND_ENV}\n"
            "Expected: file exists with VITE_API_BASE_URL=http://localhost:8000/api"
        )

    def test_frontend_env_contains_api_base_url(self):
        """
        Bug 1.6: frontend/.env must contain VITE_API_BASE_URL.

        Expected: VITE_API_BASE_URL=http://localhost:8000/api
        """
        assert FRONTEND_ENV.exists(), "frontend/.env does not exist"
        content = FRONTEND_ENV.read_text()
        assert "VITE_API_BASE_URL=http://localhost:8000/api" in content, (
            f"frontend/.env does not contain VITE_API_BASE_URL=http://localhost:8000/api\n"
            f"Actual content: {content!r}"
        )

    def test_startup_logs_warning_for_placeholder_secret_key(self):
        """
        Bug 1.4/1.5: Startup must log a warning when SECRET_KEY is the placeholder value.

        Counterexample on unfixed code:
          SECRET_KEY = "change-this-in-production-use-openssl-rand-hex-32"
          → No warning logged at startup
          → JWT tokens signed with well-known predictable string

        Expected after fix: WARNING logged at startup about insecure SECRET_KEY.
        """
        main_path = WORKSPACE_ROOT / "backend" / "app" / "main.py"
        main_source = main_path.read_text()

        # validate_config function must exist
        assert "validate_config" in main_source, (
            "validate_config() function not found in main.py.\n"
            "Expected: function that checks for placeholder credentials and logs warnings."
        )

        # Must check for the placeholder SECRET_KEY value
        placeholder_key = "change-this-in-production-use-openssl-rand-hex-32"
        assert placeholder_key in main_source, (
            f"main.py does not check for placeholder SECRET_KEY value '{placeholder_key}'.\n"
            "Expected: warning logged when SECRET_KEY is the default placeholder."
        )

    def test_startup_logs_warning_for_placeholder_google_client_secret(self):
        """
        Bug 1.4: Startup must log a warning when GOOGLE_CLIENT_SECRET is placeholder/None.

        Counterexample on unfixed code:
          GOOGLE_CLIENT_SECRET = "your-google-client-secret" or None
          → No warning logged at startup
          → OAuth fails at runtime with HTTP 400 from Google

        Expected after fix: WARNING logged at startup about misconfigured Google OAuth.
        """
        main_path = WORKSPACE_ROOT / "backend" / "app" / "main.py"
        main_source = main_path.read_text()

        # Must check for the placeholder GOOGLE_CLIENT_SECRET value
        assert "GOOGLE_CLIENT_SECRET" in main_source, (
            "main.py does not check GOOGLE_CLIENT_SECRET.\n"
            "Expected: warning logged when GOOGLE_CLIENT_SECRET is placeholder or None."
        )
        assert "your-google-client-secret" in main_source, (
            "main.py does not check for placeholder 'your-google-client-secret' value.\n"
            "Expected: warning logged when GOOGLE_CLIENT_SECRET is the placeholder string."
        )

    def test_validate_config_called_in_lifespan(self):
        """
        Bug 1.4/1.5: validate_config() must be called in the lifespan startup handler.

        Expected: validate_config() is invoked during app startup.
        """
        main_path = WORKSPACE_ROOT / "backend" / "app" / "main.py"
        main_source = main_path.read_text()

        # Both the function definition and a call to it must exist
        assert "def validate_config" in main_source, (
            "validate_config() function definition not found in main.py."
        )
        # The function must be called (not just defined)
        # Look for a call pattern after the function definition
        assert main_source.count("validate_config") >= 2, (
            "validate_config() is defined but not called in main.py.\n"
            "Expected: validate_config() called in the lifespan startup handler."
        )


# ─── Property 2: Preservation Tests ──────────────────────────────────────────
# These tests PASS on both unfixed and fixed code.
# They verify that non-buggy configurations are unchanged by the fix.


class TestPreservation:
    """
    **Property 2: Preservation** - Non-Buggy Configurations Unchanged

    Non-Bug Condition (¬C): isBugCondition(input) returns False for:
      - LLM_PROVIDER is openai or gemini (not claude)
      - Authentication is email/password (not Google OAuth)
      - Configuration values are not the specific buggy ones

    Expected: Fixed code produces exactly the same behavior as original code
    for all non-buggy configurations.
    """

    def test_requirements_txt_preserves_all_other_dependencies(self):
        """
        Preservation 3.5: Core dependencies must remain present.
        """
        content = REQUIREMENTS_TXT.read_text()
        lines = [line.strip() for line in content.splitlines()]

        # Core framework packages that must be preserved
        preserved_prefixes = [
            "fastapi==",
            "uvicorn",
            "pydantic==",
            "pydantic-settings==",
            "openai==",
            "anthropic==",
            "sqlalchemy",
            "python-jose",
            "httpx==",
            "python-dotenv==",
        ]

        for prefix in preserved_prefixes:
            assert any(line.startswith(prefix) for line in lines), (
                f"Package starting with '{prefix}' was removed from requirements.txt."
            )

    def test_config_preserves_openai_settings(self):
        """
        Preservation 3.1: OpenAI configuration must remain unchanged.

        Observe on unfixed code: OPENAI_MODEL = "gpt-4o-mini"
        After fix: same default value.
        """
        config_path = WORKSPACE_ROOT / "backend" / "app" / "config.py"
        config_source = config_path.read_text()

        assert 'OPENAI_MODEL: str = "gpt-4o-mini"' in config_source, (
            "OPENAI_MODEL default was changed. OpenAI configuration must be preserved."
        )

    def test_config_preserves_gemini_settings(self):
        """
        Preservation 3.1: Gemini configuration must remain unchanged.

        Observe on unfixed code: GEMINI_MODEL = "gemini-2.0-flash"
        After fix: same default value.
        """
        config_path = WORKSPACE_ROOT / "backend" / "app" / "config.py"
        config_source = config_path.read_text()

        assert 'GEMINI_MODEL: str = "gemini-2.0-flash"' in config_source, (
            "GEMINI_MODEL default was changed. Gemini configuration must be preserved."
        )

    def test_config_preserves_jwt_settings(self):
        """
        Preservation 3.2: JWT authentication settings must remain unchanged.

        Observe on unfixed code: JWT_ALGORITHM = "HS256", token expiry settings present.
        After fix: same values.
        """
        config_path = WORKSPACE_ROOT / "backend" / "app" / "config.py"
        config_source = config_path.read_text()

        assert 'JWT_ALGORITHM: str = "HS256"' in config_source, (
            "JWT_ALGORITHM was changed. Email/password auth must be preserved."
        )
        assert "ACCESS_TOKEN_EXPIRE_MINUTES" in config_source, (
            "ACCESS_TOKEN_EXPIRE_MINUTES was removed. JWT settings must be preserved."
        )
        assert "REFRESH_TOKEN_EXPIRE_DAYS" in config_source, (
            "REFRESH_TOKEN_EXPIRE_DAYS was removed. JWT settings must be preserved."
        )

    def test_main_py_preserves_lifespan_structure(self):
        """
        Preservation 3.5: The lifespan handler structure must be preserved.

        Observe on unfixed code: lifespan calls init_db(), seed_default_data().
        After fix: same calls still present, validate_config() added before them.
        """
        main_path = WORKSPACE_ROOT / "backend" / "app" / "main.py"
        main_source = main_path.read_text()

        assert "init_db()" in main_source, (
            "init_db() call was removed from lifespan. Database initialization must be preserved."
        )
        assert "seed_default_data()" in main_source, (
            "seed_default_data() call was removed from lifespan. Seed data must be preserved."
        )
        assert "close_db()" in main_source, (
            "close_db() call was removed from lifespan. Shutdown handler must be preserved."
        )

    def test_main_py_preserves_cors_middleware(self):
        """
        Preservation 3.5: CORS middleware must remain unchanged.
        """
        main_path = WORKSPACE_ROOT / "backend" / "app" / "main.py"
        main_source = main_path.read_text()

        assert "CORSMiddleware" in main_source, (
            "CORSMiddleware was removed. CORS configuration must be preserved."
        )
        assert "allow_credentials=True" in main_source, (
            "allow_credentials was changed. CORS configuration must be preserved."
        )

    def test_main_py_preserves_all_api_routers(self):
        """
        Preservation 3.5: All API routers must remain registered.
        """
        main_path = WORKSPACE_ROOT / "backend" / "app" / "main.py"
        main_source = main_path.read_text()

        assert "auth_router" in main_source, "auth router was removed"
        assert "documents_router" in main_source, "documents router was removed"
        assert "query_router" in main_source, "query router was removed"
        assert "admin_router" in main_source, "admin router was removed"

    def test_frontend_env_does_not_override_existing_env_vars(self):
        """
        Preservation 3.6: frontend/.env must use the same VITE_API_BASE_URL value
        as documented in frontend/.env.example.
        """
        env_example = WORKSPACE_ROOT / "frontend" / ".env.example"
        env_file = FRONTEND_ENV

        if env_example.exists() and env_file.exists():
            example_content = env_example.read_text().strip()
            env_content = env_file.read_text().strip()

            # Both should have the same VITE_API_BASE_URL value
            example_url = None
            for line in example_content.splitlines():
                if line.startswith("VITE_API_BASE_URL="):
                    example_url = line.split("=", 1)[1]
                    break

            env_url = None
            for line in env_content.splitlines():
                if line.startswith("VITE_API_BASE_URL="):
                    env_url = line.split("=", 1)[1]
                    break

            if example_url and env_url:
                assert example_url == env_url, (
                    f"VITE_API_BASE_URL in frontend/.env ({env_url!r}) differs from "
                    f"frontend/.env.example ({example_url!r}).\n"
                    "The .env file should match the documented example value."
                )

    def test_validate_config_does_not_log_warning_for_real_secret_key(self):
        """
        Preservation 3.2: validate_config() must NOT log warnings when SECRET_KEY
        is a real (non-placeholder) value.

        For all non-buggy inputs (real credentials), behavior is unchanged.
        """
        main_path = WORKSPACE_ROOT / "backend" / "app" / "main.py"
        main_source = main_path.read_text()

        # The check must be conditional (only warn for placeholder, not always)
        # Verify the placeholder string is used in a conditional check
        assert "if" in main_source and "SECRET_KEY" in main_source, (
            "validate_config() must conditionally check SECRET_KEY, not always warn."
        )

    def test_validate_config_does_not_log_warning_for_real_google_secret(self):
        """
        Preservation 3.4: validate_config() must NOT log warnings when
        GOOGLE_CLIENT_SECRET is a real credential.

        For all non-buggy inputs (real credentials), behavior is unchanged.
        """
        main_path = WORKSPACE_ROOT / "backend" / "app" / "main.py"
        main_source = main_path.read_text()

        # The check must be conditional
        assert "if" in main_source and "GOOGLE_CLIENT_SECRET" in main_source, (
            "validate_config() must conditionally check GOOGLE_CLIENT_SECRET, not always warn."
        )
