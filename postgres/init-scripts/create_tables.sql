CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INT,
    product_name VARCHAR(100),
    quantity INT,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- далее использовать TRUNCATE ... CASCADE
    CONSTRAINT orders_user_id_fk_users_id
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- initial fill users
INSERT INTO users
  (id, name, email)
VALUES
  (1, 'John Doe', 'john@example.com'),
  (2, 'Jane Smith', 'jane@example.com'),
  (3, 'Alice Johnson', 'alice@example.com'),
  (4, 'Bob Brown', 'bob@example.com')

ON CONFLICT (id) DO NOTHING
;

-- initial fill orders
INSERT INTO orders
  (id, user_id, product_name, quantity)
VALUES
  (1, 1, 'Product A', 2),
  (2, 1, 'Product B', 1),
  (3, 2, 'Product C', 5),
  (4, 3, 'Product D', 3),
  (5, 4, 'Product E', 4)

ON CONFLICT DO NOTHING
;
