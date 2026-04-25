#!/usr/bin/env python3
"""Quick balance checker for bunq sandbox."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.bunq_client import RealBunqClient

async def main():
    api_key = os.environ.get("BUNQ_API_KEY")
    if not api_key:
        print("Set BUNQ_API_KEY env var", file=sys.stderr)
        sys.exit(1)

    client = RealBunqClient(
        api_key=api_key,
        base_url="https://public-api.sandbox.bunq.com/v1",
        sandbox=True,
    )

    await client._ensure_session()
    uid = client._bunq_user_id
    print(f"User ID: {uid}\n")

    accounts_resp = await client._get(f"/user/{uid}/monetary-account")
    for item in accounts_resp.get("Response", []):
        for type_name, acct in item.items():
            print(f"Type: {type_name}")
            print(f"  ID: {acct['id']}")
            print(f"  Status: {acct.get('status', 'N/A')}")
            print(f"  Description: {acct.get('description', 'N/A')}")
            print(f"  Balance: €{acct['balance']['value']}")
            print()

    print("\nBuckets (via get_buckets):")
    buckets = await client.get_buckets()
    for b in buckets:
        print(f"  {b['id']}: {b['name']} — €{b['balance_eur']:.2f} / €{b['goal_eur']:.2f}")

    print("\nTransactions (via get_transactions):")
    tx = await client.get_transactions()
    print(f"  Account used: {tx['monetary_account_id']}")
    print(f"  Balance: €{tx['balance_eur']:.2f}")
    print(f"  Transaction count: {len(tx['transactions'])}")
    for t in tx['transactions'][:5]:
        print(f"    {t['date']} | €{t['amount_eur']:.2f} | {t['counterparty']} | {t['description']}")

if __name__ == "__main__":
    asyncio.run(main())
