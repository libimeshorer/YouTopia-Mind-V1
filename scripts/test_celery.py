#!/usr/bin/env python
"""
Celery Infrastructure Smoke Test

Tests the Celery/Redis infrastructure to ensure:
1. Redis broker is accessible
2. Celery workers are running and responding
3. Tasks are properly registered
4. Tasks can be submitted and executed

Usage:
    # Basic test (requires workers running)
    python scripts/test_celery.py

    # Test with task execution
    python scripts/test_celery.py --execute-task

    # Verbose output
    python scripts/test_celery.py -v

Prerequisites:
    1. Redis must be running (docker-compose up redis)
    2. For full tests, Celery worker must be running:
       celery -A src.workers.celery_app worker --loglevel=info
"""

import argparse
import sys
import time
from typing import Tuple

# Add project root to path
sys.path.insert(0, ".")


def test_redis_connection() -> Tuple[bool, str]:
    """Test direct Redis connection."""
    try:
        import redis
        from src.config.settings import settings

        redis_url = settings.redis_url or "redis://localhost:6379/0"
        client = redis.from_url(redis_url, socket_timeout=5)

        # Test ping
        response = client.ping()
        if response:
            # Get some info
            info = client.info("server")
            version = info.get("redis_version", "unknown")
            return True, f"Connected to Redis {version}"
        return False, "Redis ping failed"
    except Exception as e:
        return False, f"Redis connection failed: {e}"


def test_celery_app_init() -> Tuple[bool, str]:
    """Test Celery app initialization."""
    try:
        from src.workers.celery_app import celery_app

        # Check app is created
        if celery_app.main != "youtopia_agents":
            return False, f"Unexpected app name: {celery_app.main}"

        # Check broker URL is set
        broker_url = celery_app.conf.broker_url
        if not broker_url:
            return False, "Broker URL not configured"

        return True, f"Celery app initialized, broker: {broker_url[:30]}..."
    except Exception as e:
        return False, f"Celery app init failed: {e}"


def test_worker_ping() -> Tuple[bool, str]:
    """Test if Celery workers are responding."""
    try:
        from src.workers.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=5.0)
        ping_response = inspect.ping()

        if not ping_response:
            return False, "No workers responding (are workers running?)"

        workers = list(ping_response.keys())
        return True, f"Workers responding: {', '.join(workers)}"
    except Exception as e:
        return False, f"Worker ping failed: {e}"


def test_registered_tasks() -> Tuple[bool, str]:
    """Test that expected tasks are registered."""
    try:
        from src.workers.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=5.0)
        registered = inspect.registered()

        if not registered:
            return False, "No workers available to check tasks"

        # Get tasks from first worker
        first_worker = list(registered.keys())[0]
        tasks = registered[first_worker]

        # Check for our tasks
        expected_tasks = [
            "src.workers.tasks.observe_all_clones",
            "src.workers.tasks.observe_and_classify_for_clone",
        ]

        missing = [t for t in expected_tasks if t not in tasks]
        if missing:
            return False, f"Missing tasks: {missing}"

        our_tasks = [t for t in tasks if t.startswith("src.workers.tasks.")]
        return True, f"Registered tasks: {', '.join(our_tasks)}"
    except Exception as e:
        return False, f"Task registration check failed: {e}"


def test_task_execution() -> Tuple[bool, str]:
    """Test actual task execution (requires running worker)."""
    try:
        from src.workers.tasks import observe_all_clones
        from celery import states

        # Submit task
        result = observe_all_clones.apply_async()
        task_id = result.id

        # Wait for completion (max 30 seconds)
        start_time = time.time()
        timeout = 30

        while time.time() - start_time < timeout:
            if result.ready():
                break
            time.sleep(0.5)

        if not result.ready():
            return False, f"Task {task_id} did not complete within {timeout}s"

        # Check result
        if result.state == states.SUCCESS:
            return True, f"Task {task_id} completed successfully: {result.result}"
        elif result.state == states.FAILURE:
            return False, f"Task {task_id} failed: {result.result}"
        else:
            return False, f"Task {task_id} ended in unexpected state: {result.state}"

    except Exception as e:
        return False, f"Task execution failed: {e}"


def test_beat_schedule() -> Tuple[bool, str]:
    """Verify beat schedule configuration."""
    try:
        from src.workers.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        if not schedule:
            return False, "No beat schedule configured"

        # Check for observation task
        if "observe-and-classify-all-clones" not in schedule:
            return False, "Observation task not in beat schedule"

        task_config = schedule["observe-and-classify-all-clones"]
        task_name = task_config.get("task")

        if task_name != "src.workers.tasks.observe_all_clones":
            return False, f"Wrong task in schedule: {task_name}"

        return True, f"Beat schedule configured with {len(schedule)} task(s)"
    except Exception as e:
        return False, f"Beat schedule check failed: {e}"


def run_tests(execute_task: bool = False, verbose: bool = False) -> bool:
    """Run all tests and report results."""

    tests = [
        ("Redis Connection", test_redis_connection),
        ("Celery App Init", test_celery_app_init),
        ("Beat Schedule", test_beat_schedule),
        ("Worker Ping", test_worker_ping),
        ("Registered Tasks", test_registered_tasks),
    ]

    if execute_task:
        tests.append(("Task Execution", test_task_execution))

    print("=" * 60)
    print("Celery Infrastructure Smoke Test")
    print("=" * 60)
    print()

    all_passed = True
    results = []

    for name, test_func in tests:
        try:
            passed, message = test_func()
            results.append((name, passed, message))

            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {name}")
            if verbose or not passed:
                print(f"       {message}")

            if not passed:
                all_passed = False

        except Exception as e:
            results.append((name, False, str(e)))
            print(f"✗ FAIL: {name}")
            print(f"       Error: {e}")
            all_passed = False

    print()
    print("=" * 60)

    passed_count = sum(1 for _, p, _ in results if p)
    total_count = len(results)

    if all_passed:
        print(f"All tests passed ({passed_count}/{total_count})")
        print("=" * 60)
        return True
    else:
        print(f"Some tests failed ({passed_count}/{total_count} passed)")
        print("=" * 60)
        print()
        print("Troubleshooting:")
        print("  1. Ensure Redis is running: docker-compose up -d redis")
        print("  2. Start Celery worker: celery -A src.workers.celery_app worker --loglevel=info")
        print("  3. Check REDIS_URL in your environment")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Smoke test for Celery/Redis infrastructure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--execute-task",
        action="store_true",
        help="Also test actual task execution (requires running worker)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output for all tests"
    )

    args = parser.parse_args()

    success = run_tests(
        execute_task=args.execute_task,
        verbose=args.verbose
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
