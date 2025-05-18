-- 创建complaints表
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_time DATETIME,
    content TEXT,
    user_id TEXT,
    product_category TEXT
);