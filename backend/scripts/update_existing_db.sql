-- 已有开发库更新脚本。
-- 全量重建数据库时请运行 scripts/init_db.py；本文件只用于不清库的本地开发库补齐历史结构和数据。

-- 补充用户-乘机人绑定表，并用历史订单回填绑定关系。
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

-- 将燃油基建费快照固化到客票，避免航班燃油费变更影响历史订单明细。
SELECT COUNT(*) INTO @ticket_has_fuel_fee
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'ticket'
  AND column_name = 'fuel_infra_fee';

SET @add_ticket_fuel_fee = IF(
    @ticket_has_fuel_fee = 0,
    'ALTER TABLE ticket ADD COLUMN fuel_infra_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00',
    'SELECT 1'
);
PREPARE stmt FROM @add_ticket_fuel_fee;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @ticket_has_fuel_fee_check
FROM information_schema.table_constraints
WHERE constraint_schema = DATABASE()
  AND table_name = 'ticket'
  AND constraint_name = 'chk_ticket_fuel_fee';

SET @add_ticket_fuel_fee_check = IF(
    @ticket_has_fuel_fee_check = 0,
    'ALTER TABLE ticket ADD CONSTRAINT chk_ticket_fuel_fee CHECK (fuel_infra_fee >= 0)',
    'SELECT 1'
);
PREPARE stmt FROM @add_ticket_fuel_fee_check;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE ticket t
JOIN flight_instance fi ON t.instance_id = fi.instance_id
JOIN flight f ON fi.flight_no = f.flight_no
SET t.fuel_infra_fee = f.fuel_infra_fee
WHERE t.fuel_infra_fee = 0.00;
