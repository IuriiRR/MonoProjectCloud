import json
import requests
import sys
import os
import argparse
from typing import Dict, List, Any, Set

# Configuration
# Default values, can be overridden by environment variables or arguments
USERS_API_URL = os.getenv("USERS_API_URL", "http://localhost:8081")
ACCOUNTS_API_URL = os.getenv("ACCOUNTS_API_URL", "http://localhost:8082")
TRANSACTIONS_API_URL = os.getenv("TRANSACTIONS_API_URL", "http://localhost:8083")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
JSON_FILE_PATH = "monobank.json"

HEADERS = {
    "X-Internal-Api-Key": INTERNAL_API_KEY,
    "Content-Type": "application/json"
}

def load_json_dump(file_path: str) -> Dict[str, Any]:
    print(f"Loading dump from {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

def map_dependencies(dump_data: List[Dict[str, Any]]):
    """
    Extracts mappings for currencies and MCC codes from the dump.
    """
    currencies = {}
    mcc_codes = {}
    
    for item in dump_data:
        model = item.get("model")
        pk = item.get("pk")
        fields = item.get("fields", {})

        if model == "monobank.currency":
            currencies[pk] = {
                "code": fields.get("code"),
                "name": fields.get("name"),
                "flag": fields.get("flag"),
                "symbol": fields.get("symbol")
            }
        elif model == "monobank.categorymso":
            mcc_codes[pk] = fields.get("mso")
            
    return currencies, mcc_codes

def extract_transactions(dump_data: List[Dict[str, Any]], currencies: Dict, mcc_codes: Dict) -> Dict[str, List[Dict]]:
    """
    Extracts transactions from the dump and groups them by account_id.
    Returns: { account_id: [transaction_payload, ...] }
    """
    transactions_by_account = {}
    
    count = 0
    for item in dump_data:
        model = item.get("model")
        pk = item.get("pk") # Transaction ID
        fields = item.get("fields", {})
        
        if model in ["monobank.monotransaction", "monobank.jartransaction"]:
            account_id = fields.get("account") # The account ID (FK to MonoCard/MonoJar which uses string ID as PK)
            
            # In Django dump, Foreign Keys are usually the PK value. 
            # MonoCard/MonoJar PKs are the string IDs (e.g., "tier_...").
            # So 'account_id' here should be the actual string ID we need.
            
            if not account_id:
                continue

            # Resolve dependencies
            currency_pk = fields.get("currency")
            currency_data = currencies.get(currency_pk, {})
            
            mcc_pk = fields.get("mcc")
            mcc_code = mcc_codes.get(mcc_pk)
            
            # Construct payload matching TransactionCreate model
            transaction = {
                "id": pk,
                # user_id and account_id will be injected later when matching
                "time": fields.get("time"),
                "description": fields.get("description"),
                "amount": fields.get("amount"),
                "operation_amount": fields.get("operation_amount"),
                "commission_rate": fields.get("commission_rate"),
                "cashback_amount": fields.get("cashback_amount"),
                "balance": fields.get("balance"),
                "hold": fields.get("hold", False),
                "comment": fields.get("comment"),
                "mcc_code": mcc_code,
                "original_mcc": fields.get("original_mcc"),
                "currency": currency_data
            }
            
            if account_id not in transactions_by_account:
                transactions_by_account[account_id] = []
            transactions_by_account[account_id].append(transaction)
            count += 1
            
    print(f"Extracted {count} transactions from dump.")
    return transactions_by_account

def fetch_current_users() -> List[Dict]:
    print("Fetching current users...")
    try:
        resp = requests.get(f"{USERS_API_URL}/users", headers=HEADERS)
        resp.raise_for_status()
        return resp.json().get("users", [])
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

def fetch_user_accounts(user_id: str) -> List[Dict]:
    # print(f"Fetching accounts for user {user_id}...")
    try:
        resp = requests.get(f"{ACCOUNTS_API_URL}/users/{user_id}/accounts", headers=HEADERS)
        resp.raise_for_status()
        return resp.json().get("accounts", [])
    except Exception as e:
        print(f"Error fetching accounts for user {user_id}: {e}")
        return []

def fetch_existing_transaction_ids(user_id: str, account_id: str) -> Set[str]:
    # print(f"Fetching existing transactions for account {account_id}...")
    try:
        # Fetch all transactions (using a large limit)
        # Note: In a real large system, we might need pagination, but for migration this might suffice
        # The API supports 'limit'. Let's try to get a reasonable amount.
        all_ids = set()
        url = f"{TRANSACTIONS_API_URL}/users/{user_id}/accounts/{account_id}/transactions?limit=10000"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        
        txs = resp.json().get("transactions", [])
        for tx in txs:
            all_ids.add(tx.get("id"))
            
        return all_ids
    except Exception as e:
        print(f"Error fetching transactions for account {account_id}: {e}")
        return set()

def migrate_transactions(user_id: str, account_id: str, transactions: List[Dict], dry_run: bool = True):
    if not transactions:
        return

    # Add required fields
    for tx in transactions:
        tx["user_id"] = user_id
        tx["account_id"] = account_id

    print(f"  -> Ready to migrate {len(transactions)} transactions for account {account_id} (User: {user_id})")
    
    if dry_run:
        print("     [DRY RUN] Would send request now.")
        # Print sample
        # print("     Sample:", transactions[0])
        return

    try:
        # Use the PUT batch endpoint
        url = f"{TRANSACTIONS_API_URL}/users/{user_id}/accounts/{account_id}/transactions"
        # Processing in chunks if too large? 
        # The API doesn't seem to have a hard limit documented, but safer to batch if huge.
        # Let's send in batches of 500.
        batch_size = 500
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i+batch_size]
            payload = {"transactions": batch}
            resp = requests.put(url, json=payload, headers=HEADERS)
            
            if resp.status_code not in [200, 201]:
                print(f"     [ERROR] Failed to send batch {i//batch_size + 1}: {resp.text}")
            else:
                res_json = resp.json()
                print(f"     [SUCCESS] Batch {i//batch_size + 1}: Processed {res_json.get('processed')} transactions.")
                
    except Exception as e:
        print(f"     [ERROR] Exception during migration: {e}")

def main():
    parser = argparse.ArgumentParser(description="Migrate transactions from Django dump to Functions API.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing them.")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Execute actions.")
    parser.set_defaults(dry_run=True)
    args = parser.parse_args()

    print("--- Starting Migration Script ---")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE EXECUTION'}")
    
    # 1. Load Dump
    dump_data = load_json_dump(JSON_FILE_PATH)
    
    # 2. Extract Dependencies
    currencies, mcc_codes = map_dependencies(dump_data)
    
    # 3. Extract Transactions from Dump
    json_transactions_map = extract_transactions(dump_data, currencies, mcc_codes)
    
    # 4. Map Current Accounts
    users = fetch_current_users()
    print(f"Found {len(users)} users in current system.")
    
    total_missing_found = 0
    total_migrated = 0
    
    for user in users:
        user_id = user.get("user_id")
        accounts = fetch_user_accounts(user_id)
        
        for account in accounts:
            account_id = account.get("id")
            
            # Check if we have transactions for this account in the dump
            if account_id in json_transactions_map:
                candidates = json_transactions_map[account_id]
                
                # Fetch existing IDs to avoid duplicates/unnecessary writes
                existing_ids = fetch_existing_transaction_ids(user_id, account_id)
                
                missing_txs = [tx for tx in candidates if tx["id"] not in existing_ids]
                
                if missing_txs:
                    print(f"Account {account_id}: Found {len(missing_txs)} missing transactions (out of {len(candidates)} in dump).")
                    migrate_transactions(user_id, account_id, missing_txs, dry_run=args.dry_run)
                    total_missing_found += len(missing_txs)
                    if not args.dry_run:
                        total_migrated += len(missing_txs)
                else:
                    # print(f"Account {account_id}: All {len(candidates)} transactions already exist.")
                    pass
            else:
                # Account exists in current system but not in dump (or no transactions in dump)
                pass

    print("\n--- Summary ---")
    print(f"Total missing transactions identified: {total_missing_found}")
    if not args.dry_run:
        print(f"Total transactions migrated: {total_migrated}")
    else:
        print("No transactions migrated (DRY RUN). Use --no-dry-run to execute.")

if __name__ == "__main__":
    main()
