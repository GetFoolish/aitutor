#!/usr/bin/env python3
"""MongoDB health QA check.

Verifies that MongoDB connection is healthy and critical collections are accessible.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple, Dict, Any

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def check_mongodb_via_http() -> Tuple[bool, str, float]:
    """Check MongoDB health via DashSystem /health endpoint.

    Returns:
        Tuple of (passed, details, elapsed_s)
    """
    start = time.time()

    try:
        import urllib.request
        import urllib.error

        dash_base = os.environ.get("DASH_BASE", "http://localhost:8000")
        url = f"{dash_base}/health"

        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "QA-Health-Check")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                elapsed = time.time() - start
                body = response.read().decode("utf-8")

                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    return False, f"Invalid JSON response from health endpoint: {body[:100]}", elapsed

                # Check health response
                status = data.get("status", "")
                ready = data.get("ready", False)

                # Accept either status="ok" or status="ready" with ready=True
                if ready and status in ("ok", "ready"):
                    return True, f"MongoDB health check passed via {dash_base}/health (status={status}, ready={ready})", elapsed
                else:
                    return False, f"MongoDB health degraded: {data}", elapsed

        except urllib.error.HTTPError as e:
            elapsed = time.time() - start
            return False, f"HTTP error {e.code} from health endpoint: {e.reason}", elapsed

        except urllib.error.URLError as e:
            elapsed = time.time() - start
            return False, f"Failed to connect to {dash_base}: {e.reason}", elapsed

    except Exception as e:
        elapsed = time.time() - start
        return False, f"Health check failed: {e}", elapsed


def check_mongodb_direct() -> Tuple[bool, str, float]:
    """Check MongoDB connection directly using pymongo.

    Returns:
        Tuple of (passed, details, elapsed_s)
    """
    start = time.time()

    try:
        # Try to import pymongo
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
        except ImportError:
            elapsed = time.time() - start
            return False, "pymongo not available for direct MongoDB check", elapsed

        # Get MongoDB URI from environment
        mongodb_uri = os.environ.get("MONGODB_URI")
        if not mongodb_uri:
            elapsed = time.time() - start
            return False, "MONGODB_URI not set in environment", elapsed

        db_name = os.environ.get("MONGODB_DB_NAME", "ai_tutor")

        # Connect to MongoDB with short timeout
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)

        # Ping the server
        client.admin.command("ping")

        # Check database exists
        db = client[db_name]

        # Check critical collections exist
        collections = db.list_collection_names()
        critical_collections = ["users", "student_profiles", "content_pool"]

        missing_collections = [c for c in critical_collections if c not in collections]

        # Get collection stats
        stats = {}
        for coll_name in critical_collections:
            if coll_name in collections:
                coll = db[coll_name]
                count = coll.count_documents({})
                stats[coll_name] = count

        client.close()

        elapsed = time.time() - start

        if missing_collections:
            return False, f"Missing collections: {missing_collections}. Available: {collections[:10]}", elapsed
        else:
            details = f"MongoDB healthy. Collections: {stats}"
            return True, details, elapsed

    except ConnectionFailure as e:
        elapsed = time.time() - start
        return False, f"MongoDB connection failed: {e}", elapsed

    except ServerSelectionTimeoutError as e:
        elapsed = time.time() - start
        return False, f"MongoDB server selection timeout: {e}", elapsed

    except Exception as e:
        elapsed = time.time() - start
        return False, f"Direct MongoDB check failed: {e}", elapsed


def run_check() -> Tuple[bool, str, float]:
    """Run MongoDB health check.

    Tries HTTP health endpoint first, falls back to direct connection.

    Returns:
        Tuple of (passed, details, elapsed_s)
    """
    start = time.time()

    # Try HTTP health check first (faster, doesn't require pymongo)
    http_passed, http_details, http_elapsed = check_mongodb_via_http()

    if http_passed:
        return True, f"HTTP check: {http_details}", http_elapsed

    # HTTP check failed, try direct connection
    direct_passed, direct_details, direct_elapsed = check_mongodb_direct()

    total_elapsed = time.time() - start

    if direct_passed:
        return True, f"Direct check: {direct_details} (HTTP check failed: {http_details})", total_elapsed
    else:
        return False, f"Both checks failed. HTTP: {http_details}; Direct: {direct_details}", total_elapsed


def main():
    """Run check and print results."""
    passed, details, elapsed_s = run_check()

    status = "PASS" if passed else "FAIL"
    print(f"[{status}] MongoDB Health Check")
    print(f"Details: {details}")
    print(f"Elapsed: {elapsed_s:.2f}s")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
