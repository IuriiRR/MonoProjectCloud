## Firestore schema for Monobank (proposed + MVP scope)

This document describes the Firestore data model for migrating the Django `monobank` app.

### Design goals
- **Per-user isolation**: user-specific data lives under `users/{user_id}`.
- **Fast reads**: jars and their transactions are read with a single path.
- **Denormalization**: currency (and later category) is embedded to avoid extra reads.
- **Idempotent sync**: Monobank transaction IDs become Firestore document IDs.

---

## 1) `users` (top-level collection)

**Collection**: `users`  
**Document ID**: `user_id` (your internal unique user id; replaces `tg_id`)

### Fields
- **user_id**: `string` – same as document id (stored redundantly for convenience)
- **username**: `string|null` – display name
- **mono_token**: `string` – Monobank API token (MVP stores it here; later move to Secret Manager or per-user encrypted storage)
- **active**: `boolean` – whether this user should be synced
- **created_at**: `timestamp`
- **updated_at**: `timestamp`

---

## 2) `accounts` (subcollection: jars + cards)

**Path**: `users/{user_id}/accounts`  
**Document ID**: `account_id` (Monobank `id` for card/jar)

MVP focuses on `type="jar"` documents, but the model is future-proof for cards.

### Common fields
- **id**: `string` – same as doc id
- **type**: `"jar"|"card"`
- **send_id**: `string|null`
- **currency**: `map` – denormalized currency
- **balance**: `number`
- **is_active**: `boolean`
- **created_at**: `timestamp`
- **updated_at**: `timestamp`

### Jar-only fields (from Monobank)
- **title**: `string|null`
- **goal**: `number|null`

### App-owned jar fields (NOT from Monobank; should be preserved by sync)
- **is_budget**: `boolean` (default `false`)
- **invested**: `number` (default `0`)

### Currency denormalization

Instead of referencing a `currencies/{code}` document, we embed:

```json
{
  "currency": {
    "code": 980,
    "name": "UAH",
    "symbol": "₴",
    "flag": "🇺🇦"
  }
}
```

The catalog is sourced from `cloud_api/seed/currency.json` (copied from `django_api/api/currency.json`).

---

## 3) `transactions` (jar transactions subcollection)

**Path**: `users/{user_id}/accounts/{jar_id}/transactions`  
**Document ID**: `transaction_id` (Monobank statement item `id`)

### Fields (MVP)
- **id**: `string` (same as doc id)
- **time**: `number` (unix timestamp)
- **description**: `string|null`
- **amount**: `number`
- **operation_amount**: `number|null`
- **commission_rate**: `number|null`
- **cashback_amount**: `number|null`
- **balance**: `number`
- **hold**: `boolean`
- **comment**: `string|null`
- **mcc_code**: `number|null` (Monobank `mcc`)
- **original_mcc**: `number|null`
- **currency**: `map` (denormalized currency)
- **created_at**: `timestamp`
- **updated_at**: `timestamp`

### Category denormalization (TODO)

Your target schema embeds:

```json
{
  "category": {
    "name": "Transport",
    "symbol": "🚕",
    "mcc": 5411
  }
}
```

MVP currently stores **only** `mcc_code` and does not resolve `category` yet.
Next step: import `categories.json` / `categories_mso.json` into Firestore `categories` and join during sync.

---

## Query patterns
- **List jars for a user**: `users/{user}/accounts` where `type=="jar"` (optionally `is_active==true`)
- **Transactions for a jar**: `users/{user}/accounts/{jar}/transactions` ordered by `time desc`, optionally filtered by `time >= X`

---

## Notes / tradeoffs
- Denormalization means currency changes require fanout updates; acceptable because currency metadata is stable.
- Public rules are used only for local emulator; production must use auth + security rules.


