#!/usr/bin/env python3
"""
Environment Configuration Health Check

Validates current environment configuration and provides safety report.
Run this before performing any production operations.

Usage:
  python scripts/check_environment.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings
from src.utils.environment import (
    get_environment,
    is_production,
    is_development,
    validate_environment_config,
    log_environment_info,
)
from src.utils.logging import configure_logging, get_logger

configure_logging("INFO")
logger = get_logger(__name__)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def check_environment_variable():
    """Check 1: Environment Variable"""
    print_header("Check 1: Environment Variable")
    
    env = get_environment()
    env_var = os.getenv("ENVIRONMENT", "").strip()
    
    if env_var:
        print_success(f"ENVIRONMENT variable is set: '{env_var}'")
    else:
        print_warning("ENVIRONMENT variable is not set - defaulting to 'development' (safety default)")
    
    print_info(f"Detected environment: {env}")
    
    if is_production():
        print_warning("⚠️  PRODUCTION ENVIRONMENT DETECTED")
        print_warning("   All operations will affect production data. Exercise extreme caution.")
    elif is_development():
        print_success("Development environment - safe for testing")
    else:
        print_error(f"Unknown environment: {env}")
        return False
    
    return True


def check_resource_configuration():
    """Check 2: Resource Configuration"""
    print_header("Check 2: Resource Configuration")
    
    print_info("Pinecone Configuration:")
    print(f"  Index Name: {settings.pinecone_index_name or 'Not set'}")
    print(f"  API Key: {'*' * 20}...{settings.pinecone_api_key[-4:] if settings.pinecone_api_key and len(settings.pinecone_api_key) > 4 else '***'}")
    
    print_info("AWS S3 Configuration:")
    print(f"  Bucket Name: {settings.s3_bucket_name or 'Not set'}")
    print(f"  Region: {settings.aws_region}")
    print(f"  Access Key: {'*' * 20}...{settings.aws_access_key_id[-4:] if settings.aws_access_key_id and len(settings.aws_access_key_id) > 4 else '***'}")
    
    print_info("Database Configuration:")
    db_url = settings.database_url or "Not set"
    if db_url != "Not set" and "://" in db_url:
        # Mask credentials
        try:
            parts = db_url.split("://")
            if len(parts) == 2:
                scheme = parts[0]
                rest = parts[1]
                if "/" in rest:
                    host_part, db_part = rest.split("/", 1)
                    if "@" in host_part:
                        _, host = host_part.rsplit("@", 1)
                        masked = f"{scheme}://***:***@{host}/{db_part}"
                    else:
                        masked = f"{scheme}://{host_part}/{db_part}"
                else:
                    masked = f"{scheme}://***:***@{rest}"
            else:
                masked = "***"
        except Exception:
            masked = "*** (error parsing)"
        print(f"  URL: {masked}")
    else:
        print(f"  URL: {db_url}")
    
    return True


def check_resource_validation():
    """Check 3: Resource Name Validation"""
    print_header("Check 3: Resource Name Validation")
    
    is_valid, warnings = validate_environment_config()
    
    if is_valid:
        print_success("All resource names match environment expectations")
        return True
    else:
        print_warning(f"Found {len(warnings)} resource name mismatch(es):")
        for warning in warnings:
            print_warning(f"  - {warning}")
        print_warning("\n⚠️  Review the warnings above - resource names may not match environment")
        return False


def check_required_settings():
    """Check 4: Required Settings"""
    print_header("Check 4: Required Settings")
    
    issues = []
    
    if not settings.pinecone_api_key:
        issues.append("PINECONE_API_KEY is not set")
    else:
        print_success("Pinecone API key is set")
    
    if not settings.pinecone_index_name:
        issues.append("PINECONE_INDEX_NAME is not set")
    else:
        print_success(f"Pinecone index name is set: {settings.pinecone_index_name}")
    
    if not settings.openai_api_key:
        issues.append("OPENAI_API_KEY is not set")
    else:
        print_success("OpenAI API key is set")
    
    if not settings.database_url:
        issues.append("DATABASE_URL is not set")
    else:
        print_success("Database URL is set")
    
    if settings.s3_bucket_name:
        print_success(f"S3 bucket name is set: {settings.s3_bucket_name}")
    else:
        print_info("S3 bucket name is not set (optional for some operations)")
    
    if issues:
        print_error("Missing required settings:")
        for issue in issues:
            print_error(f"  - {issue}")
        return False
    
    return True


def check_database_safety():
    """Check 5: Database Connection Safety"""
    print_header("Check 5: Database Connection Safety")
    
    env = get_environment()
    db_url = settings.database_url or ""
    
    if not db_url:
        print_warning("Database URL is not set - skipping database safety check")
        return True
    
    if env == "production":
        if "localhost" in db_url.lower() or "127.0.0.1" in db_url.lower():
            print_error("⚠️  CRITICAL: Production environment but database URL contains localhost/127.0.0.1")
            print_error("   Production should use remote database (e.g., Render PostgreSQL)")
            print_error("   This may indicate a configuration error!")
            return False
        else:
            print_success("Production environment with remote database (correct)")
    else:
        # Development - localhost is fine
        print_success("Development environment - localhost database is acceptable")
    
    return True


def generate_summary(results: dict):
    """Generate summary report"""
    print_header("Environment Health Check Summary")
    
    all_passed = all(results.values())
    
    for check_name, passed in results.items():
        status = f"{Colors.GREEN}PASSED{Colors.RESET}" if passed else f"{Colors.RED}FAILED{Colors.RESET}"
        print(f"  {check_name:30} {status}")
    
    print()
    
    if all_passed:
        env = get_environment()
        if is_production():
            print(f"{Colors.BOLD}{Colors.YELLOW}")
            print("╔" + "="*68 + "╗")
            print("║" + " "*68 + "║")
            print("║" + "  ✓ All checks passed - Production environment verified".center(68) + "║")
            print("║" + " "*68 + "║")
            print("║" + "  ⚠️  REMEMBER: You are in PRODUCTION mode".center(68) + "║")
            print("║" + "     All operations will affect production data".center(68) + "║")
            print("║" + " "*68 + "║")
            print("╚" + "="*68 + "╝")
            print(Colors.RESET)
        else:
            print(f"{Colors.BOLD}{Colors.GREEN}")
            print("╔" + "="*68 + "╗")
            print("║" + " "*68 + "║")
            print("║" + "  ✓ All checks passed - Environment ready for operations".center(68) + "║")
            print("║" + " "*68 + "║")
            print("╚" + "="*68 + "╝")
            print(Colors.RESET)
        return 0
    else:
        print(f"{Colors.BOLD}{Colors.RED}")
        print("╔" + "="*68 + "╗")
        print("║" + " "*68 + "║")
        print("║" + "  ✗ Some checks failed - Review issues above".center(68) + "║")
        print("║" + " "*68 + "║")
        print("║" + "  Do not proceed with production operations until".center(68) + "║")
        print("║" + "  all issues are resolved".center(68) + "║")
        print("║" + " "*68 + "║")
        print("╚" + "="*68 + "╝")
        print(Colors.RESET)
        return 1


def main():
    """Run environment health check"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  Environment Configuration Health Check".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    print(Colors.RESET)
    
    results = {}
    
    # Run all checks
    results["Environment Variable"] = check_environment_variable()
    results["Resource Configuration"] = check_resource_configuration()
    results["Resource Validation"] = check_resource_validation()
    results["Required Settings"] = check_required_settings()
    results["Database Safety"] = check_database_safety()
    
    # Generate summary
    exit_code = generate_summary(results)
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
