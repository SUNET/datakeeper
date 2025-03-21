CREATE TABLE IF NOT EXISTS policy (
    -- id INTEGER PRIMARY KEY,
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    policy_file TEXT NOT NULL,
    is_enabled INTEGER NOT NULL CHECK (is_enabled IN (0, 1)),
    strategy TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (json_valid(data_type)),  -- JSON constraint
    tags TEXT NOT NULL CHECK (json_valid(tags)),          -- JSON constraint
    paths TEXT NOT NULL CHECK (json_valid(paths)),        -- JSON constraint
    operations TEXT NOT NULL CHECK (json_valid(operations)),        -- JSON constraint
    triggers TEXT NOT NULL CHECK (json_valid(triggers)),        -- JSON constraint
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job (
    -- id INTEGER PRIMARY KEY,
    id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL,
    name TEXT NOT NULL,
    operation TEXT NOT NULL,
    filetypes TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_spec TEXT NOT NULL CHECK (json_valid(trigger_spec)),  -- JSON constraint
    status TEXT CHECK (status IN ('added', 'scheduled', 'running', 'success', 'failed')),
    last_error TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run_time TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (policy_id) REFERENCES policy (id) ON DELETE CASCADE
);