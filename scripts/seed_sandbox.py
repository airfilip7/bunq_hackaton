#!/usr/bin/env python3
"""Seed a bunq sandbox account with money and optionally create a second bucket.

Usage:
    export BUNQ_API_KEY=sandbox_xxxx
    python scripts/seed_sandbox.py
"""

import argparse
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.bunq_client import RealBunqClient

SANDBOX_BASE_URL = "https://public-api.sandbox.bunq.com/v1"


async def main():
    parser = argparse.ArgumentParser(description="Seed bunq sandbox account")
    parser.add_argument("--api-key", default=os.environ.get("BUNQ_API_KEY"), help="bunq sandbox API key")
    parser.add_argument("--fund", type=float, default=5000.0, help="Amount to fund main account with (EUR)")
    parser.add_argument("--create-bucket", action="store_true", help="Also create a second savings bucket")
    parser.add_argument("--bucket-name", default="House Fund", help="Name for second bucket")
    parser.add_argument("--bucket-goal", type=float, default=55000.0, help="Goal for second bucket (EUR)")
    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: Provide --api-key or set BUNQ_API_KEY env var", file=sys.stderr)
        sys.exit(1)

    client = RealBunqClient(
        api_key=args.api_key,
        base_url=SANDBOX_BASE_URL,
        sandbox=True,
    )

    print("Establishing session...")
    await client._ensure_session()
    print(f"  Session OK — user_id={client._bunq_user_id}")

    print("\nFetching accounts...")
    tx_info = await client.get_transactions()
    main_account_id = tx_info["monetary_account_id"]
    print(f"  Main account: {main_account_id}")
    print(f"  Current balance: €{tx_info['balance_eur']:.2f}")

    if args.fund > 0:
        print(f"\nRequesting €{args.fund:.2f} from sugar daddy...")
        body = {
            "amount_inquired": {"value": str(args.fund), "currency": "EUR"},
            "counterparty_alias": {"type": "EMAIL", "value": "sugardaddy@bunq.com"},
            "description": "bunq Nest seed funding",
            "allow_bunqme": False,
        }
        await client._post(f"/user/{client._bunq_user_id}/monetary-account/{main_account_id}/request-inquiry", body)
        print("  Request sent. Waiting 4s for auto-accept...")
        await asyncio.sleep(4)

        tx_info = await client.get_transactions()
        print(f"  New balance: €{tx_info['balance_eur']:.2f}")

    second_bucket_id = None
    if args.create_bucket:
        print(f"\nCreating bucket '{args.bucket_name}'...")
        bucket = await client.create_bucket(name=args.bucket_name, goal_eur=args.bucket_goal)
        second_bucket_id = bucket["id"]
        print(f"  Created: id={bucket['id']}, name={bucket['name']}, goal=€{bucket['goal_eur']:.2f}")

    print("\n--- Summary ---")
    print(f"API_KEY={args.api_key}")
    print(f"MAIN_ACCOUNT={main_account_id}")
    if second_bucket_id:
        print(f"SECOND_BUCKET={second_bucket_id}")
    print("---------------")


if __name__ == "__main__":
    asyncio.run(main())
