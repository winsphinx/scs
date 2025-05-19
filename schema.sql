-- 创建complaints表
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_time DATETIME NOT NULL,
    content TEXT NOT NULL,
    user_id TEXT NOT NULL,
    product_category TEXT NOT NULL,
    reply TEXT
);