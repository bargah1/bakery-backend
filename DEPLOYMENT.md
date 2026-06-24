# DEPLOYMENT.md
# Deploying Bakery AI Manager to Supabase (Option B — Full Migration)

This guide walks you through deploying the fully migrated backend to Supabase.

---

## Prerequisites

- [Supabase account](https://supabase.com) (free tier works)
- [Supabase CLI](https://supabase.com/docs/guides/cli) installed
- Node.js 18+ (for Supabase CLI)
- Python 3.9+ (for data migration script only)

Install the Supabase CLI:
```bash
npm install -g supabase
```

---

## Step 1: Create Supabase Project

1. Go to [app.supabase.com](https://app.supabase.com) → **New Project**
2. Choose a name (e.g., `bakery-ai-manager`), set a strong DB password
3. Copy your **Project URL** and **Service Role Key** from:  
   `Project Settings → API`

---

## Step 2: Run the Database Schema

1. Go to **SQL Editor** in your Supabase dashboard
2. Open and paste the entire contents of `supabase_schema.sql`
3. Click **Run**
4. Verify all 12 tables are created under **Table Editor**

---

## Step 3: Create Storage Bucket

In the SQL editor, run:
```sql
INSERT INTO storage.buckets (id, name, public)
VALUES ('product-images', 'product-images', true)
ON CONFLICT (id) DO NOTHING;
```

Or via the dashboard: **Storage → New bucket → Name: `product-images` → Public: ON**

---

## Step 4: Set Up Supabase CLI & Login

```bash
supabase login
supabase link --project-ref YOUR_PROJECT_REF
```

Find `YOUR_PROJECT_REF` in your project URL: `https://YOUR_PROJECT_REF.supabase.co`

---

## Step 5: Set Edge Function Secrets

```bash
supabase secrets set GOOGLE_API_KEY=AIza...
supabase secrets set GOOGLE_CLOUD_PROJECT=your-gcp-project-id
supabase secrets set GOOGLE_TTS_API_KEY=AIza...
supabase secrets set REPLICATE_API_TOKEN=r8_...
```

> The `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are automatically available inside Edge Functions — you don't need to set them manually.

---

## Step 6: Deploy All Edge Functions

From the `bakery-backend/` directory:

```bash
supabase functions deploy outlets
supabase functions deploy expenses
supabase functions deploy items
supabase functions deploy items-pos
supabase functions deploy sales
supabase functions deploy production
supabase functions deploy staff
supabase functions deploy reports
supabase functions deploy ownerbot
```

Or deploy all at once:
```bash
supabase functions deploy
```

---

## Step 7: Migrate Existing Data (Firestore → Supabase)

If you have existing data in Firebase, run the migration script:

```bash
# Install dependencies
pip install firebase-admin supabase python-dotenv

# Set env vars (copy .env.example to .env and fill in values)
cp .env.example .env
# Edit .env with your actual keys

# Run migration
python migrate_firestore_to_supabase.py
```

---

## Step 8: Update Your Frontend

Replace all API calls that pointed to Render with your Supabase Edge Function URLs.

**Old Render URL pattern:**
```
https://bakery-backend-5qkn.onrender.com/sales/process/
```

**New Supabase Edge Function URL pattern:**
```
https://YOUR_PROJECT_REF.supabase.co/functions/v1/sales
```

### Full URL Mapping

| Old Endpoint (Render/Django)              | New Endpoint (Supabase Edge Function)                         |
|-------------------------------------------|----------------------------------------------------------------|
| `GET /outlets/manage/`                    | `GET  /functions/v1/outlets`                                   |
| `POST /outlets/manage/`                   | `POST /functions/v1/outlets`                                   |
| `PUT /outlets/manage/<id>/`               | `PUT  /functions/v1/outlets/<id>`                             |
| `DELETE /outlets/manage/<id>/`            | `DELETE /functions/v1/outlets/<id>`                           |
| `GET /expenses/manage/`                   | `GET  /functions/v1/expenses`                                  |
| `POST /expenses/manage/`                  | `POST /functions/v1/expenses`                                  |
| `GET /items/manage-products/`             | `GET  /functions/v1/items/manage-products/`                    |
| `POST /items/manage-products/`            | `POST /functions/v1/items/manage-products/`                    |
| `GET /items/manage-products/<id>/`        | `GET  /functions/v1/items/manage-products/<id>/`               |
| `PUT /items/manage-products/<id>/`        | `PUT  /functions/v1/items/manage-products/<id>/`               |
| `DELETE /items/manage-products/<id>/`     | `DELETE /functions/v1/items/manage-products/<id>/`             |
| `GET /items/inventory-report/`            | `GET  /functions/v1/items/inventory-report/`                   |
| `GET /items/generate-barcode/`            | `GET  /functions/v1/items/generate-barcode/`                   |
| `POST /items/upload-image/`               | `POST /functions/v1/items/upload-image/`                       |
| `GET /items/pos/products/`                | `GET  /functions/v1/items-pos`                                 |
| `POST /sales/process/`                    | `POST /functions/v1/sales/process`                             |
| `POST /sales/record-sale/`                | `POST /functions/v1/sales/record-sale`                         |
| `GET /sales/summary-report/`              | `GET  /functions/v1/sales/summary-report`                      |
| `GET /sales/structured-report/`           | `GET  /functions/v1/sales/structured-report`                   |
| `GET /sales/history/`                     | `GET  /functions/v1/sales/history`                             |
| `GET /sales/find/<bill_id>/`              | `GET  /functions/v1/sales/find/<bill_id>`                      |
| `DELETE /sales/delete-range/`             | `DELETE /functions/v1/sales/delete-range`                      |
| `POST /production/record/`                | `POST /functions/v1/production/record`                         |
| `GET /production/recipes/`                | `GET  /functions/v1/production/recipes`                        |
| `POST /production/recipes/`               | `POST /functions/v1/production/recipes`                        |
| `GET /production/ingredients/all/`        | `GET  /functions/v1/production/ingredients/all`                |
| `GET /production/structured-report/`      | `GET  /functions/v1/production/structured-report`              |
| `GET /staff/list/`                        | `GET  /functions/v1/staff/list`                                |
| `POST /staff/add/`                        | `POST /functions/v1/staff/add`                                 |
| `DELETE /staff/delete/<id>/`              | `DELETE /functions/v1/staff/delete/<id>`                       |
| `PUT /staff/edit/<id>/`                   | `PUT  /functions/v1/staff/edit/<id>`                           |
| `POST /staff/punch-attendance/`           | `POST /functions/v1/staff/punch-attendance`                    |
| `GET /staff/attendance-report/`           | `GET  /functions/v1/staff/attendance-report`                   |
| `POST /staff/staff/salary/mark-paid/`     | `POST /functions/v1/staff/salary/mark-paid`                    |
| `GET /reports/dashboard-summary/`         | `GET  /functions/v1/reports/dashboard-summary`                 |
| `GET /reports/profit-loss/`               | `GET  /functions/v1/reports/profit-loss`                       |
| `GET /reports/low-stock-alerts/`          | `GET  /functions/v1/reports/low-stock-alerts`                  |
| `DELETE /reports/clear-data/`             | `DELETE /functions/v1/reports/clear-data`                      |
| `POST /ownerbot/ask/`                     | `POST /functions/v1/ownerbot/ask`                              |
| `POST /ownerbot/parse-order/`             | `POST /functions/v1/ownerbot/parse-order`                      |

---

## Step 9: Verify

1. Test a simple endpoint in your browser or Postman:
   ```
   GET https://YOUR_PROJECT_REF.supabase.co/functions/v1/outlets
   Headers: Authorization: Bearer YOUR_ANON_KEY
   ```
2. Check Supabase **Functions Logs** for errors
3. Verify data in **Table Editor**

---

## Architecture After Migration

```
Frontend Apps (billing.html, pos, ownerbot UI)
        │
        ▼
Supabase Edge Functions (Deno/TypeScript)
  ├── /functions/v1/outlets
  ├── /functions/v1/expenses
  ├── /functions/v1/items
  ├── /functions/v1/items-pos
  ├── /functions/v1/sales
  ├── /functions/v1/production
  ├── /functions/v1/staff
  ├── /functions/v1/reports
  └── /functions/v1/ownerbot  ← calls Gemini, Translate, TTS APIs
        │
        ▼
Supabase PostgreSQL (12 tables)
        │
        ▼
Supabase Storage (product images)
```

**Zero cost on Supabase free tier** for this workload. No Render, no Firebase billing.
