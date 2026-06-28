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

-- 将航班实例固化为当天实际承运信息，避免修改航班模板影响已生成实例。
SELECT COUNT(*) INTO @fi_has_scheduled_departure
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'flight_instance'
  AND column_name = 'scheduled_departure';

SET @add_fi_scheduled_departure = IF(
    @fi_has_scheduled_departure = 0,
    'ALTER TABLE flight_instance ADD COLUMN scheduled_departure TIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_fi_scheduled_departure;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @fi_has_scheduled_arrival
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'flight_instance'
  AND column_name = 'scheduled_arrival';

SET @add_fi_scheduled_arrival = IF(
    @fi_has_scheduled_arrival = 0,
    'ALTER TABLE flight_instance ADD COLUMN scheduled_arrival TIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_fi_scheduled_arrival;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @fi_has_fuel_fee
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'flight_instance'
  AND column_name = 'fuel_infra_fee';

SET @add_fi_fuel_fee = IF(
    @fi_has_fuel_fee = 0,
    'ALTER TABLE flight_instance ADD COLUMN fuel_infra_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00',
    'SELECT 1'
);
PREPARE stmt FROM @add_fi_fuel_fee;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @fi_has_adjusted_at
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'flight_instance'
  AND column_name = 'adjusted_at';

SET @add_fi_adjusted_at = IF(
    @fi_has_adjusted_at = 0,
    'ALTER TABLE flight_instance ADD COLUMN adjusted_at DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_fi_adjusted_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @fi_has_departure_adjusted_at
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'flight_instance'
  AND column_name = 'scheduled_departure_adjusted_at';

SET @add_fi_departure_adjusted_at = IF(
    @fi_has_departure_adjusted_at = 0,
    'ALTER TABLE flight_instance ADD COLUMN scheduled_departure_adjusted_at DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_fi_departure_adjusted_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @fi_has_arrival_adjusted_at
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'flight_instance'
  AND column_name = 'scheduled_arrival_adjusted_at';

SET @add_fi_arrival_adjusted_at = IF(
    @fi_has_arrival_adjusted_at = 0,
    'ALTER TABLE flight_instance ADD COLUMN scheduled_arrival_adjusted_at DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_fi_arrival_adjusted_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @fi_has_dep_airport_adjusted_at
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'flight_instance'
  AND column_name = 'dep_airport_adjusted_at';

SET @add_fi_dep_airport_adjusted_at = IF(
    @fi_has_dep_airport_adjusted_at = 0,
    'ALTER TABLE flight_instance ADD COLUMN dep_airport_adjusted_at DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_fi_dep_airport_adjusted_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @fi_has_arr_airport_adjusted_at
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'flight_instance'
  AND column_name = 'arr_airport_adjusted_at';

SET @add_fi_arr_airport_adjusted_at = IF(
    @fi_has_arr_airport_adjusted_at = 0,
    'ALTER TABLE flight_instance ADD COLUMN arr_airport_adjusted_at DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_fi_arr_airport_adjusted_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE flight_instance fi
JOIN flight f ON fi.flight_no = f.flight_no
SET fi.scheduled_departure = COALESCE(fi.scheduled_departure, f.scheduled_departure),
    fi.scheduled_arrival = COALESCE(fi.scheduled_arrival, f.scheduled_arrival),
    fi.fuel_infra_fee = IF(@fi_has_fuel_fee = 0, f.fuel_infra_fee, fi.fuel_infra_fee);

ALTER TABLE flight_instance MODIFY COLUMN scheduled_departure TIME NOT NULL;
ALTER TABLE flight_instance MODIFY COLUMN scheduled_arrival TIME NOT NULL;

SELECT COUNT(*) INTO @fi_has_fuel_fee_check
FROM information_schema.table_constraints
WHERE constraint_schema = DATABASE()
  AND table_name = 'flight_instance'
  AND constraint_name = 'chk_instance_fuel_fee';

SET @add_fi_fuel_fee_check = IF(
    @fi_has_fuel_fee_check = 0,
    'ALTER TABLE flight_instance ADD CONSTRAINT chk_instance_fuel_fee CHECK (fuel_infra_fee >= 0)',
    'SELECT 1'
);
PREPARE stmt FROM @add_fi_fuel_fee_check;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE OR REPLACE VIEW v_flight_search AS
SELECT
    fi.instance_id,
    fi.flight_no,
    fi.flight_date,
    fi.status AS instance_status,
    fi.scheduled_departure,
    fi.scheduled_arrival,
    fi.fuel_infra_fee,
    f.dep_airport_code,
    dep_apt.city_name AS dep_city,
    f.arr_airport_code,
    arr_apt.city_name AS arr_city,
    f.airline_code,
    al.airline_name,
    f.aircraft_model,
    fi.economy_left,
    fi.first_left
FROM flight_instance fi
JOIN flight f ON fi.flight_no = f.flight_no
JOIN airport dep_apt ON f.dep_airport_code = dep_apt.iata_code
JOIN airport arr_apt ON f.arr_airport_code = arr_apt.iata_code
JOIN airline al ON f.airline_code = al.iata_code
WHERE fi.status = '可订';