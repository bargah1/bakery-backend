-- =======================================================
-- Supabase PostgreSQL Schema for Bakery AI Manager
-- Replaces all Firebase Firestore collections
-- =======================================================

-- 1. Outlets
CREATE TABLE IF NOT EXISTS outlets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    type TEXT DEFAULT 'sales' CHECK (type IN ('sales', 'production'))
);

-- 2. Items (Products)
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC DEFAULT 0,
    stock NUMERIC DEFAULT 0,
    unit_type TEXT DEFAULT 'piece',
    low_stock_threshold NUMERIC DEFAULT 10.0,
    barcode TEXT,
    type TEXT DEFAULT 'production',
    cost_price NUMERIC DEFAULT 0.0,
    image_url TEXT DEFAULT '',
    is_active BOOLEAN DEFAULT TRUE,
    outlet_ids TEXT[] DEFAULT '{}',
    malayalam_name TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Recipes
CREATE TABLE IF NOT EXISTS recipes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    unit_type TEXT,
    ingredients JSONB DEFAULT '[]'::jsonb,
    shelf_life_days INTEGER,
    calories NUMERIC,
    energy NUMERIC,
    nutrition_info JSONB,
    rate NUMERIC
);

-- 4. Sales
CREATE TABLE IF NOT EXISTS sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    numeric_bill_id TEXT,
    total_amount NUMERIC DEFAULT 0,
    total_cogs NUMERIC DEFAULT 0,
    items JSONB DEFAULT '[]'::jsonb,
    outlet_id TEXT REFERENCES outlets(id),
    staff_id TEXT,
    customer_id TEXT DEFAULT 'anonymous',
    payment_method TEXT,
    payment_status TEXT DEFAULT 'Paid'
);

-- Index for common sales queries
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date);
CREATE INDEX IF NOT EXISTS idx_sales_outlet_date ON sales(outlet_id, date);
CREATE INDEX IF NOT EXISTS idx_sales_numeric_bill_id ON sales(numeric_bill_id);
CREATE INDEX IF NOT EXISTS idx_sales_customer_id ON sales(customer_id);

-- 5. Production Logs
CREATE TABLE IF NOT EXISTS production_logs (
    batch_id TEXT PRIMARY KEY,
    recipe_id TEXT REFERENCES recipes(id),
    quantity_produced NUMERIC DEFAULT 0,
    production_unit_id TEXT REFERENCES outlets(id),
    total_cost NUMERIC DEFAULT 0,
    date TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_production_logs_date ON production_logs(date);
CREATE INDEX IF NOT EXISTS idx_production_logs_unit_date ON production_logs(production_unit_id, date);

-- 6. Outlet Ingredients (replaces Firestore subcollection outlets/{id}/ingredients)
CREATE TABLE IF NOT EXISTS outlet_ingredients (
    id TEXT NOT NULL,
    outlet_id TEXT NOT NULL REFERENCES outlets(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    unit TEXT,
    stock NUMERIC DEFAULT 0,
    cost_per_unit NUMERIC DEFAULT 0,
    low_stock_threshold NUMERIC DEFAULT 0,
    PRIMARY KEY (id, outlet_id)
);

CREATE INDEX IF NOT EXISTS idx_outlet_ingredients_outlet ON outlet_ingredients(outlet_id);

-- 7. Staff
CREATE TABLE IF NOT EXISTS staff (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT,
    contact_number TEXT,
    address TEXT DEFAULT '',
    emergency_contact TEXT DEFAULT '',
    image_urls JSONB DEFAULT '[]'::jsonb,
    face_encodings JSONB DEFAULT '[]'::jsonb,
    location_id TEXT DEFAULT '',
    salary NUMERIC DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Attendance Records (clock_in / clock_out punches)
CREATE TABLE IF NOT EXISTS attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id TEXT REFERENCES staff(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    punch_type TEXT NOT NULL CHECK (punch_type IN ('clock_in', 'clock_out')),
    timestamp TEXT NOT NULL,
    location_id TEXT DEFAULT '',
    staff_name TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_attendance_staff_date ON attendance_records(staff_id, date);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance_records(date);

-- 9. Attendance (simple status-based: present/absent/leave)
CREATE TABLE IF NOT EXISTS attendance (
    id TEXT PRIMARY KEY,
    staff_id TEXT REFERENCES staff(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Salary Payments
CREATE TABLE IF NOT EXISTS salary_payments (
    id TEXT PRIMARY KEY,
    staff_id TEXT REFERENCES staff(id) ON DELETE CASCADE,
    amount NUMERIC DEFAULT 0,
    payment_date TEXT,
    period_start TEXT,
    period_end TEXT,
    expense_doc_id TEXT
);

-- 11. Expenses
CREATE TABLE IF NOT EXISTS expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description TEXT,
    amount NUMERIC DEFAULT 0,
    category TEXT,
    date TEXT NOT NULL,
    outlet_id TEXT DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);

-- 12. CCTV Observations
CREATE TABLE IF NOT EXISTS cctv_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id TEXT,
    staff_name TEXT,
    detected_activity TEXT,
    camera_id TEXT,
    date TEXT,
    timestamp TEXT,
    confidence NUMERIC
);

-- =======================================================
-- PostgreSQL Functions (RPC) for atomic operations
-- =======================================================

-- Decrement item stock atomically
CREATE OR REPLACE FUNCTION decrement_stock(item_id TEXT, qty NUMERIC)
RETURNS VOID AS $$
BEGIN
    UPDATE items SET stock = stock - qty WHERE id = item_id;
END;
$$ LANGUAGE plpgsql;

-- Increment item stock atomically
CREATE OR REPLACE FUNCTION increment_stock(item_id TEXT, qty NUMERIC)
RETURNS VOID AS $$
BEGIN
    UPDATE items SET stock = stock + qty WHERE id = item_id;
END;
$$ LANGUAGE plpgsql;

-- Decrement ingredient stock atomically
CREATE OR REPLACE FUNCTION decrement_ingredient_stock(
    p_ingredient_id TEXT,
    p_outlet_id TEXT,
    p_qty NUMERIC
)
RETURNS VOID AS $$
BEGIN
    UPDATE outlet_ingredients 
    SET stock = stock - p_qty 
    WHERE id = p_ingredient_id AND outlet_id = p_outlet_id;
END;
$$ LANGUAGE plpgsql;

-- Record production with full transaction:
-- 1. Deduct ingredients from the production unit
-- 2. Increment the finished product stock
-- 3. Log the production batch
CREATE OR REPLACE FUNCTION record_production_transaction(
    p_batch_id TEXT,
    p_recipe_id TEXT,
    p_quantity NUMERIC,
    p_production_unit_id TEXT,
    p_ingredients JSONB,  -- Array of {id, quantity_needed}
    p_date TEXT,
    p_timestamp TIMESTAMPTZ
)
RETURNS JSONB AS $$
DECLARE
    ingredient JSONB;
    ing_id TEXT;
    ing_qty_needed NUMERIC;
    ing_stock NUMERIC;
    ing_cost_per_unit NUMERIC;
    ing_name TEXT;
    total_batch_cost NUMERIC := 0;
BEGIN
    -- For each ingredient, check stock and deduct
    FOR ingredient IN SELECT * FROM jsonb_array_elements(p_ingredients)
    LOOP
        ing_id := ingredient->>'id';
        ing_qty_needed := (ingredient->>'quantity')::NUMERIC * p_quantity;
        
        -- Get current ingredient stock
        SELECT stock, cost_per_unit, name INTO ing_stock, ing_cost_per_unit, ing_name
        FROM outlet_ingredients 
        WHERE id = ing_id AND outlet_id = p_production_unit_id;
        
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Ingredient "%" not found in this unit.', ing_id;
        END IF;
        
        IF ing_qty_needed > ing_stock THEN
            RAISE EXCEPTION 'Not enough stock for %. Required: %, Available: %', ing_name, ing_qty_needed, ing_stock;
        END IF;
        
        -- Deduct ingredient
        UPDATE outlet_ingredients 
        SET stock = stock - ing_qty_needed 
        WHERE id = ing_id AND outlet_id = p_production_unit_id;
        
        total_batch_cost := total_batch_cost + (ing_qty_needed * ing_cost_per_unit);
    END LOOP;
    
    -- Increment finished product stock
    UPDATE items SET stock = stock + p_quantity WHERE id = p_recipe_id;
    
    -- Log the production
    INSERT INTO production_logs (batch_id, recipe_id, quantity_produced, production_unit_id, total_cost, date, timestamp)
    VALUES (p_batch_id, p_recipe_id, p_quantity, p_production_unit_id, total_batch_cost, p_date, p_timestamp);
    
    RETURN jsonb_build_object('batch_id', p_batch_id, 'total_cost', total_batch_cost);
END;
$$ LANGUAGE plpgsql;

-- Create Supabase Storage bucket for product images
-- (Run this via Supabase Dashboard or SQL editor)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('product-images', 'product-images', true);
