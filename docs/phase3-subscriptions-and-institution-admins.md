# Phase 3 — Subscriptions and institution administration

## Subscription entitlement

Every student and mentor account begins on the institution-level **basic** plan on the day that the account completes registration. A subscription cycle lasts one calendar month.

| Plan | AI credits per cycle |
| --- | ---: |
| Basic | 10 |
| Pro | 50 |
| Ultra | 100 |
| Max | 200 |

Light and Standard AI models cost one credit; Expert (MiniMax M3) costs two. The project-wide daily ceiling remains a server-side safety guard, but it does not replace the individual subscription balance.

- At each cycle boundary, the balance resets to the plan allowance.
- Redeeming a premium key starts a new premium cycle immediately.
- A premium plan stays fixed while active; it cannot switch to a different premium tier or be manually downgraded.
- When a premium cycle ends without another eligible renewal, the account returns to Basic. The premium end timestamp becomes the new Basic cycle day and the balance resets to 10.

## Institution-scoped premium keys

Super administrators allocate available Pro, Ultra, and Max key inventory to an institution. Institution administrators can issue a key only from their assigned institution's available inventory.

- Format: `XX-X-XXXX-XXX`.
- Keys are generated with CSPRNG characters, stored only as Argon2id hash plus a keyed HMAC fingerprint, and protected by a unique database constraint.
- Administrators select a tier and an in-range quantity, then receive one XLSX receipt for the complete batch. Plaintext exists only in that downloaded receipt; it is never stored or available later.
- Both the interface and the locked server-side allocation row reject quantities above the institution's remaining inventory. The batch is atomic: inventory is deducted only if every Key is issued.
- A key is bound to the issuing institution abbreviation. A different institution's account cannot activate it.
- Issuing a key consumes one matching inventory item. An unactivated key can be reclaimed exactly once; it becomes permanently revoked and restores that inventory item. Activated keys cannot be reclaimed.

## Administration scope

The legacy `admin` role remains a super-administrator alias to preserve Alpha accounts. The new roles are:

- `super_admin`: can manage all student and mentor accounts, select from imported institutions, allocate premium inventory, and assign or remove institution administrators.
- `institution_admin`: receives one or more explicit institution scopes. Assignment requires selecting a verified, active student or mentor account that already belongs to the chosen institution; the API never accepts a free-text institution or account name. The API filters user lists and rejects view, update, batch-status, password-reset, and dashboard requests outside those scopes.

The frontend mirrors these server-side boundaries: institution administrators see student management, mentor management, and subscription-key operations; super administrators also see cross-institution functions.

## AI conversation retention

AI conversations are permanently owned by the account that created them. Users can delete individual conversations. The server serializes creation per account and retains at most 100 conversation records, automatically deleting the oldest records (with their messages) when the cap is exceeded.
