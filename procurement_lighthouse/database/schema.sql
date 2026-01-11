-- Procurement Lighthouse PoC Database Schema
-- Optimized for AWS t2.micro Free Tier (1GB RAM)

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Inventory snapshot table with indexes for performance
CREATE TABLE IF NOT EXISTS inventory (
    item_id SERIAL PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL,
    current_stock INTEGER NOT NULL DEFAULT 0,
    safety_stock INTEGER NOT NULL DEFAULT 0,
    unit_cost DECIMAL(10,2),
    location VARCHAR(100),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for frequent queries
CREATE INDEX IF NOT EXISTS idx_inventory_stock_levels ON inventory(current_stock, safety_stock);
CREATE INDEX IF NOT EXISTS idx_inventory_location ON inventory(location);

-- Purchase orders table
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expected_delivery DATE,
    total_value DECIMAL(12,2)
);

-- Index for status and delivery queries
CREATE INDEX IF NOT EXISTS idx_po_status ON purchase_orders(status);
CREATE INDEX IF NOT EXISTS idx_po_delivery ON purchase_orders(expected_delivery);

-- Purchase order line items
CREATE TABLE IF NOT EXISTS po_line_items (
    line_id SERIAL PRIMARY KEY,
    po_id INTEGER REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES inventory(item_id) ON DELETE CASCADE,
    quantity_ordered INTEGER NOT NULL,
    unit_price DECIMAL(10,2),
    quantity_received INTEGER DEFAULT 0
);

-- Index for joins
CREATE INDEX IF NOT EXISTS idx_po_line_items_po_id ON po_line_items(po_id);
CREATE INDEX IF NOT EXISTS idx_po_line_items_item_id ON po_line_items(item_id);

-- Consumption history
CREATE TABLE IF NOT EXISTS consumption_history (
    consumption_id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES inventory(item_id) ON DELETE CASCADE,
    quantity_consumed INTEGER NOT NULL,
    consumption_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    consumption_reason VARCHAR(100),
    department VARCHAR(100)
);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_consumption_date ON consumption_history(consumption_date);
CREATE INDEX IF NOT EXISTS idx_consumption_item_date ON consumption_history(item_id, consumption_date);

-- ML forecasts
CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES inventory(item_id) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    predicted_consumption INTEGER,
    confidence_score DECIMAL(5,4) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    confidence_lower INTEGER,
    confidence_upper INTEGER,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for forecast queries
CREATE INDEX IF NOT EXISTS idx_forecasts_item_date ON forecasts(item_id, forecast_date);
CREATE INDEX IF NOT EXISTS idx_forecasts_created ON forecasts(created_at);

-- Risk predictions table for ML stockout risk assessments
CREATE TABLE IF NOT EXISTS risk_predictions (
    prediction_id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES inventory(item_id) ON DELETE CASCADE,
    risk_probability DECIMAL(5,4) NOT NULL CHECK (risk_probability >= 0 AND risk_probability <= 1),
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    days_until_stockout INTEGER,
    model_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for risk prediction queries
CREATE INDEX IF NOT EXISTS idx_risk_predictions_item_created ON risk_predictions(item_id, created_at);
CREATE INDEX IF NOT EXISTS idx_risk_predictions_risk_level ON risk_predictions(risk_level);
CREATE INDEX IF NOT EXISTS idx_risk_predictions_created ON risk_predictions(created_at);

-- Alerts and exceptions
CREATE TABLE IF NOT EXISTS alerts (
    alert_id SERIAL PRIMARY KEY,
    alert_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    item_id INTEGER REFERENCES inventory(item_id) ON DELETE SET NULL,
    po_id INTEGER REFERENCES purchase_orders(po_id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);

-- Index for alert queries
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_type_severity ON alerts(alert_type, severity);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);

-- Event log for debugging and monitoring (lightweight)
CREATE TABLE IF NOT EXISTS event_log (
    event_id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_duration_ms INTEGER
);

-- Index for event monitoring
CREATE INDEX IF NOT EXISTS idx_event_log_type_time ON event_log(event_type, processed_at);

-- System health metrics (minimal for t2.micro)
CREATE TABLE IF NOT EXISTS system_metrics (
    metric_id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for metrics queries
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_time ON system_metrics(metric_name, recorded_at);

-- Event notification functions and triggers
-- Function to notify inventory changes
CREATE OR REPLACE FUNCTION notify_inventory_change()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('inventory_changed', 
        json_build_object(
            'item_id', COALESCE(NEW.item_id, OLD.item_id),
            'old_quantity', COALESCE(OLD.current_stock, 0),
            'new_quantity', COALESCE(NEW.current_stock, 0),
            'change_type', TG_OP,
            'timestamp', CURRENT_TIMESTAMP
        )::text
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Function to notify PO status changes
CREATE OR REPLACE FUNCTION notify_po_change()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('po_status_changed', 
        json_build_object(
            'po_id', COALESCE(NEW.po_id, OLD.po_id),
            'old_status', COALESCE(OLD.status, ''),
            'new_status', COALESCE(NEW.status, ''),
            'change_type', TG_OP,
            'timestamp', CURRENT_TIMESTAMP
        )::text
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Function to notify alert generation
CREATE OR REPLACE FUNCTION notify_alert_generated()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM pg_notify('alert_generated', 
            json_build_object(
                'alert_id', NEW.alert_id,
                'alert_type', NEW.alert_type,
                'severity', NEW.severity,
                'item_id', NEW.item_id,
                'po_id', NEW.po_id,
                'timestamp', NEW.created_at
            )::text
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to notify forecast updates
CREATE OR REPLACE FUNCTION notify_forecast_update()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        PERFORM pg_notify('forecast_updated', 
            json_build_object(
                'forecast_id', NEW.forecast_id,
                'item_id', NEW.item_id,
                'forecast_date', NEW.forecast_date,
                'predicted_consumption', NEW.predicted_consumption,
                'timestamp', NEW.created_at
            )::text
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for event notifications
DROP TRIGGER IF EXISTS trigger_inventory_change ON inventory;
CREATE TRIGGER trigger_inventory_change
    AFTER INSERT OR UPDATE OR DELETE ON inventory
    FOR EACH ROW EXECUTE FUNCTION notify_inventory_change();

DROP TRIGGER IF EXISTS trigger_po_change ON purchase_orders;
CREATE TRIGGER trigger_po_change
    AFTER INSERT OR UPDATE OR DELETE ON purchase_orders
    FOR EACH ROW EXECUTE FUNCTION notify_po_change();

DROP TRIGGER IF EXISTS trigger_alert_generated ON alerts;
CREATE TRIGGER trigger_alert_generated
    AFTER INSERT ON alerts
    FOR EACH ROW EXECUTE FUNCTION notify_alert_generated();

DROP TRIGGER IF EXISTS trigger_forecast_update ON forecasts;
CREATE TRIGGER trigger_forecast_update
    AFTER INSERT OR UPDATE ON forecasts
    FOR EACH ROW EXECUTE FUNCTION notify_forecast_update();

-- Create views for common dashboard queries (optimized for t2.micro)
CREATE OR REPLACE VIEW inventory_status AS
SELECT 
    i.item_id,
    i.item_name,
    i.current_stock,
    i.safety_stock,
    i.location,
    CASE 
        WHEN i.current_stock <= i.safety_stock THEN 'LOW'
        WHEN i.current_stock <= i.safety_stock * 1.5 THEN 'MEDIUM'
        ELSE 'HIGH'
    END as stock_level,
    i.last_updated
FROM inventory i;

CREATE OR REPLACE VIEW active_alerts AS
SELECT 
    a.alert_id,
    a.alert_type,
    a.severity,
    a.message,
    a.created_at,
    i.item_name,
    po.supplier_name
FROM alerts a
LEFT JOIN inventory i ON a.item_id = i.item_id
LEFT JOIN purchase_orders po ON a.po_id = po.po_id
WHERE a.status = 'active'
ORDER BY a.created_at DESC;

CREATE OR REPLACE VIEW po_summary AS
SELECT 
    po.po_id,
    po.supplier_name,
    po.status,
    po.created_date,
    po.expected_delivery,
    po.total_value,
    COUNT(pli.line_id) as line_items_count,
    SUM(pli.quantity_ordered) as total_quantity_ordered,
    SUM(pli.quantity_received) as total_quantity_received
FROM purchase_orders po
LEFT JOIN po_line_items pli ON po.po_id = pli.po_id
GROUP BY po.po_id, po.supplier_name, po.status, po.created_date, po.expected_delivery, po.total_value;

-- Insert PostgreSQL configuration optimizations for t2.micro
-- These would typically be set in postgresql.conf, but included here for reference
COMMENT ON DATABASE procurement_lighthouse IS 'Optimized for t2.micro: shared_buffers=128MB, max_connections=20, effective_cache_size=512MB, work_mem=4MB';