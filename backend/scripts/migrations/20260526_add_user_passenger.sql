-- 为已有开发库新增用户-乘机人绑定关系，并用历史订单回填常用乘机人。

CREATE TABLE IF NOT EXISTS user_passenger (
    user_id     BIGINT UNSIGNED NOT NULL,
    id_no       VARCHAR(32)     NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, id_no),
    KEY idx_user_passenger_id_no (id_no),
    CONSTRAINT fk_user_passenger_user FOREIGN KEY (user_id)
        REFERENCES user(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_user_passenger_passenger FOREIGN KEY (id_no)
        REFERENCES passenger(id_no) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO user_passenger (user_id, id_no)
SELECT DISTINCT o.user_id, t.passenger_id
FROM aptorder o
JOIN ticket t ON t.order_no = o.order_no
JOIN passenger p ON p.id_no = t.passenger_id;
