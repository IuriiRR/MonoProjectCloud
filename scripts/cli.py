import os
import sys
from datetime import datetime, timezone
import collections

# Add project root to path so we can import from functions
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from functions.users_api.firestore_client import get_db

def print_header(title: str):
    print(f"\n{'='*50}\n{title.center(50)}\n{'='*50}")

def get_users(db):
    users = []
    for doc in db.collection("users").stream():
        users.append(doc.to_dict())
    return users

def get_accounts(db, user_id):
    accounts = []
    # According to schema, path is users/{user_id}/accounts
    for doc in db.collection("users").document(user_id).collection("accounts").stream():
        accounts.append(doc.to_dict())
    return accounts

def draw_bar_chart(data_points: list[tuple[str, float]], title: str):
    print(f"\n--- {title} ---")
    if not data_points:
        print("No data available.")
        return

    max_val = max(v for _, v in data_points) if data_points else 0
    if max_val <= 0:
        max_val = 1  # prevent div by zero
        
    bar_max_width = 40
    for label, value in data_points:
        bar_len = int((value / max_val) * bar_max_width)
        bar = '█' * bar_len
        print(f"{label} | {bar} {value:,.2f}")

def select_account(accounts):
    print("\nAvailable Accounts:")
    for i, acc in enumerate(accounts):
        title = acc.get("title") or "Unnamed"
        print(f"[{i+1}] {title} (ID: {acc.get('id')})")
    while True:
        try:
            choice = input("\nSelect account number (or 'q' to cancel): ")
            if choice.lower() == 'q': return None
            idx = int(choice) - 1
            if 0 <= idx < len(accounts):
                return accounts[idx]
            print("Invalid choice.")
        except ValueError:
            print("Please enter a number.")

def flow_accounts_overview(db, user):
    print_header(f"Accounts Overview for {user.get('username', 'Unknown')}")
    accounts = get_accounts(db, user["user_id"])
    if not accounts:
        print("No accounts found.")
        return

    print(f"{'Name':<20} | {'Type':<6} | {'Balance':>12} | {'Currency'}")
    print("-" * 55)
    for acc in accounts:
        title = acc.get("title") or "Unnamed"
        # Truncate title
        if len(title) > 18: title = title[:15] + "..."
        bal = (acc.get("balance") or 0) / 100.0
        cur = acc.get("currency", {}).get("code", "UNK")
        print(f"{title:<20} | {acc.get('type', 'N/A'):<6} | {bal:>12.2f} | {cur}")

def flow_total_wealth(db, user):
    print_header(f"Total Wealth for {user.get('username', 'Unknown')}")
    accounts = get_accounts(db, user["user_id"])
    
    wealth_by_currency = collections.defaultdict(float)
    for acc in accounts:
        bal = (acc.get("balance") or 0) / 100.0
        cur = acc.get("currency", {}).get("code", "UNK")
        wealth_by_currency[cur] += bal
        
    for cur, total in wealth_by_currency.items():
        print(f"{cur}: {total:,.2f}")

def flow_monthly_chart(db, user):
    print_header("Monthly Balance Chart")
    accounts = get_accounts(db, user["user_id"])
    jars = [a for a in accounts if a.get("type") == "jar"]
    if not jars:
        print("No jars found for user.")
        return
        
    acc = select_account(jars)
    if not acc: return

    print("\nFetching transactions (this may take a moment)...")
    tx_ref = db.collection("users").document(user["user_id"]).collection("accounts").document(acc["id"]).collection("transactions")
    # Fetch all to bucket by month
    transactions = list(tx_ref.order_by("time").stream())
    
    if not transactions:
        print("No transactions found for this jar.")
        return

    # Bucket by YYYY-MM
    monthly_balance = {}
    for tx_doc in transactions:
        tx = tx_doc.to_dict()
        # time is unix timestamp
        dt = datetime.fromtimestamp(tx.get("time", 0), tz=timezone.utc)
        month_key = dt.strftime("%Y-%m")
        # Overwrite to get the latest balance for that month
        monthly_balance[month_key] = (tx.get("balance") or 0) / 100.0

    # Sort and prepare chart
    sorted_months = sorted(monthly_balance.keys())
    data_points = [(m, monthly_balance[m]) for m in sorted_months]
    
    title = acc.get("title") or "Unnamed Jar"
    draw_bar_chart(data_points, f"Monthly Balance: {title}")

def flow_recent_transactions(db, user):
    print_header("Recent Transactions")
    accounts = get_accounts(db, user["user_id"])
    if not accounts:
        print("No accounts found.")
        return
        
    acc = select_account(accounts)
    if not acc: return

    tx_ref = db.collection("users").document(user["user_id"]).collection("accounts").document(acc["id"]).collection("transactions")
    # Descending order, limit 10
    recent = tx_ref.order_by("time", direction="DESCENDING").limit(10).stream()
    
    print("\nLast 10 transactions:")
    print(f"{'Date':<20} | {'Amount':>10} | {'Balance':>10} | {'Description'}")
    print("-" * 75)
    for tx_doc in recent:
        tx = tx_doc.to_dict()
        dt = datetime.fromtimestamp(tx.get("time", 0), tz=timezone.utc)
        dt_str = dt.strftime("%Y-%m-%d %H:%M")
        amt = (tx.get("amount") or 0) / 100.0
        bal = (tx.get("balance") or 0) / 100.0
        desc = tx.get("description") or ""
        if len(desc) > 25: desc = desc[:22] + "..."
        print(f"{dt_str:<20} | {amt:>10.2f} | {bal:>10.2f} | {desc}")

def user_menu(db, user):
    while True:
        print_header(f"Menu: {user.get('username', 'Unknown')} ({user['user_id']})")
        print("1. Accounts Overview")
        print("2. Total Wealth")
        print("3. Monthly Balance Chart (Jars)")
        print("4. Recent Transactions")
        print("5. Switch User")
        print("0. Exit")
        
        choice = input("\nSelect an option: ")
        if choice == '1':
            flow_accounts_overview(db, user)
        elif choice == '2':
            flow_total_wealth(db, user)
        elif choice == '3':
            flow_monthly_chart(db, user)
        elif choice == '4':
            flow_recent_transactions(db, user)
        elif choice == '5':
            return True # signal to switch user
        elif choice == '0':
            print("Exiting.")
            sys.exit(0)
        else:
            print("Invalid option.")

def main():
    if not os.getenv("FIRESTORE_EMULATOR_HOST"):
        print("WARNING: FIRESTORE_EMULATOR_HOST is not set.")
        print("You are either connecting to production OR you forgot to set the emulator var.")
        print("Use: FIRESTORE_EMULATOR_HOST=localhost:8080 python cli.py")
        confirm = input("Continue anyway? (y/N): ")
        if confirm.lower() != 'y':
            sys.exit(1)

    print("Connecting to Firestore...")
    try:
        db = get_db()
    except Exception as e:
        print(f"Failed to initialize Firestore client: {e}")
        sys.exit(1)

    while True:
        print_header("Firestore Admin CLI")
        users = get_users(db)
        if not users:
            print("No users found in the database. Exiting.")
            sys.exit(0)

        print("Available Users:")
        for i, u in enumerate(users):
            print(f"[{i+1}] {u.get('username', 'Unknown')} (ID: {u.get('user_id')}) - Active: {u.get('active')}")
        
        choice = input("\nSelect a user number (or 'q' to quit): ")
        if choice.lower() == 'q':
            sys.exit(0)
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(users):
                selected_user = users[idx]
                switch = user_menu(db, selected_user)
                if not switch:
                    break
            else:
                print("Invalid choice.")
        except ValueError:
            print("Please enter a valid number.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)
