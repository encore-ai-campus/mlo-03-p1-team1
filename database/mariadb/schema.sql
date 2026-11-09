-- REFERENCE ONLY: generated from Alembic; apply migrations instead.
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 08ee866a73c5

CREATE TABLE contents (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    source VARCHAR(30) NOT NULL, 
    source_id VARCHAR(100) NOT NULL, 
    title VARCHAR(300) NOT NULL, 
    subtitle VARCHAR(300) NOT NULL, 
    category VARCHAR(20) NOT NULL, 
    region VARCHAR(30) NOT NULL, 
    venue VARCHAR(200) NOT NULL, 
    address VARCHAR(400) NOT NULL, 
    start_date DATE NOT NULL, 
    end_date DATE NOT NULL, 
    price INTEGER NOT NULL, 
    price_text VARCHAR(200) NOT NULL, 
    description TEXT NOT NULL, 
    image_url VARCHAR(1000) NOT NULL, 
    source_url VARCHAR(1000) NOT NULL, 
    tags JSON NOT NULL, 
    is_sample BOOL NOT NULL, 
    bookable BOOL NOT NULL, 
    collected_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_content_price CHECK (price >= 0), 
    CONSTRAINT uq_content_source UNIQUE (source, source_id)
);

CREATE INDEX ix_contents_category_end ON contents (category, end_date);

CREATE INDEX ix_contents_end_date ON contents (end_date);

CREATE TABLE users (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    email VARCHAR(254) NOT NULL, 
    name VARCHAR(40) NOT NULL, 
    password_hash VARCHAR(256) NOT NULL, 
    categories JSON NOT NULL, 
    tags JSON NOT NULL, 
    survey_completed BOOL NOT NULL, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (email)
);

CREATE TABLE webhook_receipts (
    event_id VARCHAR(200) NOT NULL, 
    payment_id VARCHAR(64) NOT NULL, 
    received_at DATETIME NOT NULL, 
    PRIMARY KEY (event_id)
);

CREATE TABLE auth_sessions (
    token_hash VARCHAR(64) NOT NULL, 
    user_id INTEGER NOT NULL, 
    expires_at DATETIME NOT NULL, 
    PRIMARY KEY (token_hash), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at);

CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id);

CREATE TABLE behavior_events (
    event_id VARCHAR(36) NOT NULL, 
    event_type VARCHAR(40) NOT NULL, 
    user_id INTEGER, 
    content_id INTEGER, 
    occurred_at DATETIME NOT NULL, 
    properties JSON NOT NULL, 
    PRIMARY KEY (event_id), 
    FOREIGN KEY(content_id) REFERENCES contents (id) ON DELETE SET NULL, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_events_user_time ON behavior_events (user_id, occurred_at);

CREATE TABLE bookmarks (
    user_id INTEGER NOT NULL, 
    content_id INTEGER NOT NULL, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (user_id, content_id), 
    FOREIGN KEY(content_id) REFERENCES contents (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE orders (
    payment_id VARCHAR(64) NOT NULL, 
    user_id INTEGER NOT NULL, 
    content_id INTEGER NOT NULL, 
    idempotency_key VARCHAR(36) NOT NULL, 
    order_name VARCHAR(300) NOT NULL, 
    quantity INTEGER NOT NULL, 
    amount INTEGER NOT NULL, 
    currency VARCHAR(10) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    created_at DATETIME NOT NULL, 
    updated_at DATETIME NOT NULL, 
    PRIMARY KEY (payment_id), 
    CONSTRAINT ck_order_amount CHECK (amount > 0 AND quantity BETWEEN 1 AND 4), 
    FOREIGN KEY(content_id) REFERENCES contents (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    CONSTRAINT uq_order_idempotency UNIQUE (user_id, idempotency_key)
);

CREATE INDEX ix_orders_user_id ON orders (user_id);

CREATE TABLE reviews (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    user_id INTEGER NOT NULL, 
    content_id INTEGER NOT NULL, 
    rating INTEGER NOT NULL, 
    body TEXT NOT NULL, 
    updated_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_review_rating CHECK (rating BETWEEN 1 AND 5), 
    FOREIGN KEY(content_id) REFERENCES contents (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_review_user_content UNIQUE (user_id, content_id)
);

CREATE INDEX ix_reviews_content_id ON reviews (content_id);

CREATE TABLE payment_history (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    payment_id VARCHAR(64) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    amount INTEGER NOT NULL, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(payment_id) REFERENCES orders (payment_id)
);

CREATE INDEX ix_payment_history_payment_id ON payment_history (payment_id);

CREATE TABLE reservations (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    payment_id VARCHAR(64) NOT NULL, 
    user_id INTEGER NOT NULL, 
    content_id INTEGER NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(content_id) REFERENCES contents (id), 
    FOREIGN KEY(payment_id) REFERENCES orders (payment_id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    UNIQUE (payment_id)
);

CREATE INDEX ix_reservations_user_id ON reservations (user_id);

INSERT INTO alembic_version (version_num) VALUES ('08ee866a73c5');

-- Running upgrade 08ee866a73c5 -> 30943449ef19

ALTER TABLE orders ADD COLUMN cancelled_amount INTEGER NOT NULL DEFAULT '0';

ALTER TABLE payment_history ADD COLUMN cancelled_amount INTEGER NOT NULL DEFAULT '0';

ALTER TABLE payment_history ADD COLUMN provider_transaction_id VARCHAR(200) NOT NULL DEFAULT '';

UPDATE alembic_version SET version_num='30943449ef19' WHERE alembic_version.version_num = '08ee866a73c5';

-- Running upgrade 30943449ef19 -> 65e5c5f31b9a

ALTER TABLE users ADD COLUMN gender VARCHAR(20);

ALTER TABLE users ADD COLUMN age INTEGER;

ALTER TABLE users ADD COLUMN age_recorded_at DATETIME;

ALTER TABLE users ADD COLUMN residence VARCHAR(30);

ALTER TABLE users ADD COLUMN occupation VARCHAR(80);

ALTER TABLE users ADD COLUMN mbti VARCHAR(4);

ALTER TABLE users ADD CONSTRAINT ck_user_age CHECK (age BETWEEN 0 AND 120);

UPDATE alembic_version SET version_num='65e5c5f31b9a' WHERE alembic_version.version_num = '30943449ef19';

-- Running upgrade 65e5c5f31b9a -> 78a3b1c2d4e5 (reference only; apply with Alembic)
CREATE TABLE event_outbox (
    event_id VARCHAR(36) NOT NULL PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at DATETIME NOT NULL,
    delivered_at DATETIME NULL,
    last_error VARCHAR(80) NULL,
    FOREIGN KEY (event_id) REFERENCES behavior_events(event_id) ON DELETE CASCADE
);
CREATE INDEX ix_outbox_pending ON event_outbox (delivered_at, next_attempt_at);
UPDATE alembic_version SET version_num='78a3b1c2d4e5' WHERE alembic_version.version_num='65e5c5f31b9a';

