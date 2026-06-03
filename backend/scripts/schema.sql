-- ============================================================
-- FudanAir 航空票务系统数据库结构
-- MySQL 8.0+ / InnoDB / utf8mb4
--
-- 说明：
-- 1. 本文件负责建表和视图，不创建/切换数据库。
-- 2. init_db.py 负责创建并选中 fudan_air。
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ---------- 航班侧基础数据 ----------

CREATE TABLE city (
    city_name VARCHAR(32) NOT NULL,
    PRIMARY KEY (city_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE airport (
    iata_code     CHAR(3)       NOT NULL,
    airport_name  VARCHAR(128)  NOT NULL,
    city_name     VARCHAR(32)   NOT NULL,
    PRIMARY KEY (iata_code),
    KEY idx_airport_city (city_name),
    CONSTRAINT fk_airport_city FOREIGN KEY (city_name)
        REFERENCES city(city_name) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE city_near_apt (
    city_name  VARCHAR(32)  NOT NULL,
    iata_code  CHAR(3)      NOT NULL,
    distance   DECIMAL(6,2) NOT NULL,
    PRIMARY KEY (city_name, iata_code),
    KEY idx_near_apt_iata (iata_code),
    CONSTRAINT fk_near_city FOREIGN KEY (city_name)
        REFERENCES city(city_name) ON DELETE CASCADE,
    CONSTRAINT fk_near_airport FOREIGN KEY (iata_code)
        REFERENCES airport(iata_code) ON DELETE CASCADE,
    CONSTRAINT chk_near_distance CHECK (distance >= 0 AND distance <= 300)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE airline (
    iata_code     CHAR(2)       NOT NULL,
    airline_name  VARCHAR(128)  NOT NULL,
    PRIMARY KEY (iata_code),
    UNIQUE KEY uk_airline_name (airline_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE aircraft_type (
    model          VARCHAR(32)       NOT NULL,
    economy_seats  SMALLINT UNSIGNED NOT NULL,
    first_seats    SMALLINT UNSIGNED NOT NULL,
    PRIMARY KEY (model),
    CONSTRAINT chk_aircraft_economy_seats CHECK (economy_seats >= 0),
    CONSTRAINT chk_aircraft_first_seats CHECK (first_seats >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 航班计划 ----------

CREATE TABLE flight (
    flight_no            VARCHAR(8)    NOT NULL,
    scheduled_departure  TIME          NOT NULL,
    scheduled_arrival    TIME          NOT NULL,
    fuel_infra_fee       DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    dep_airport_code     CHAR(3)       NOT NULL,
    dep_terminal         VARCHAR(8)    DEFAULT NULL,
    arr_airport_code     CHAR(3)       NOT NULL,
    arr_terminal         VARCHAR(8)    DEFAULT NULL,
    airline_code         CHAR(2)       NOT NULL,
    aircraft_model       VARCHAR(32)   NOT NULL,
    PRIMARY KEY (flight_no),
    KEY idx_flight_route (dep_airport_code, arr_airport_code),
    KEY idx_flight_airline (airline_code),
    KEY idx_flight_aircraft (aircraft_model),
    CONSTRAINT fk_flight_dep FOREIGN KEY (dep_airport_code)
        REFERENCES airport(iata_code),
    CONSTRAINT fk_flight_arr FOREIGN KEY (arr_airport_code)
        REFERENCES airport(iata_code),
    CONSTRAINT fk_flight_airline FOREIGN KEY (airline_code)
        REFERENCES airline(iata_code),
    CONSTRAINT fk_flight_aircraft FOREIGN KEY (aircraft_model)
        REFERENCES aircraft_type(model),
    CONSTRAINT chk_flight_fee CHECK (fuel_infra_fee >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE flight_weekday (
    flight_no  VARCHAR(8) NOT NULL,
    weekday    TINYINT    NOT NULL,
    PRIMARY KEY (flight_no, weekday),
    KEY idx_weekday_flight (weekday, flight_no),
    CONSTRAINT fk_fw_flight FOREIGN KEY (flight_no)
        REFERENCES flight(flight_no) ON DELETE CASCADE,
    CONSTRAINT chk_weekday CHECK (weekday BETWEEN 1 AND 7)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE flight_stopover (
    flight_no     VARCHAR(8)       NOT NULL,
    stop_order    TINYINT UNSIGNED NOT NULL,
    airport_code  CHAR(3)          NOT NULL,
    PRIMARY KEY (flight_no, stop_order),
    KEY idx_stopover_airport (airport_code),
    CONSTRAINT fk_fs_flight FOREIGN KEY (flight_no)
        REFERENCES flight(flight_no) ON DELETE CASCADE,
    CONSTRAINT fk_fs_airport FOREIGN KEY (airport_code)
        REFERENCES airport(iata_code),
    CONSTRAINT chk_stop_order CHECK (stop_order >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 航班实例与库存 ----------

CREATE TABLE flight_instance (
    instance_id   VARCHAR(32)       NOT NULL,
    flight_no     VARCHAR(8)        NOT NULL,
    flight_date   DATE              NOT NULL,
    economy_left  SMALLINT UNSIGNED NOT NULL,
    first_left    SMALLINT UNSIGNED NOT NULL,
    status        ENUM('计划','可订','已起飞','已到达','已取消')
                  NOT NULL DEFAULT '计划',
    PRIMARY KEY (instance_id),
    UNIQUE KEY uk_instance_flight_date (flight_no, flight_date),
    KEY idx_instance_date_status (flight_date, status),
    CONSTRAINT fk_fi_flight FOREIGN KEY (flight_no)
        REFERENCES flight(flight_no),
    CONSTRAINT chk_instance_economy_left CHECK (economy_left >= 0),
    CONSTRAINT chk_instance_first_left CHECK (first_left >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cabin_price (
    instance_id      VARCHAR(32)       NOT NULL,
    cabin_class      ENUM('经济舱','头等舱') NOT NULL,
    fare_type        ENUM('标准','特价')     NOT NULL DEFAULT '标准',
    price            DECIMAL(10,2)     NOT NULL,
    available_seats  SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (instance_id, cabin_class, fare_type),
    KEY idx_cabin_price_instance (instance_id),
    CONSTRAINT fk_cp_instance FOREIGN KEY (instance_id)
        REFERENCES flight_instance(instance_id) ON DELETE CASCADE,
    CONSTRAINT chk_cp_price CHECK (price >= 0),
    CONSTRAINT chk_cp_available_seats CHECK (available_seats >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 用户与乘机人 ----------

CREATE TABLE user (
    user_id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_password  VARCHAR(255)    NOT NULL,
    name           VARCHAR(64)     NOT NULL,
    phone          VARCHAR(20)     NOT NULL,
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_user_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE passenger (
    id_no       VARCHAR(32) NOT NULL,
    real_name   VARCHAR(64) NOT NULL,
    birth_date  DATE        NOT NULL,
    PRIMARY KEY (id_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE user_passenger (
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

-- ---------- 订单、客票与退改记录 ----------

CREATE TABLE aptorder (
    order_no      VARCHAR(32)     NOT NULL,
    user_id       BIGINT UNSIGNED NOT NULL,
    total_amount  DECIMAL(12,2)   NOT NULL,
    status        ENUM('待支付','已支付','已取消','已完成','部分退款','已完成退款')
                  NOT NULL DEFAULT '待支付',
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_no),
    KEY idx_order_user_created (user_id, created_at DESC),
    KEY idx_order_status_created (status, created_at),
    CONSTRAINT fk_order_user FOREIGN KEY (user_id)
        REFERENCES user(user_id),
    CONSTRAINT chk_order_amount CHECK (total_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE ticket (
    ticket_no     VARCHAR(32)  NOT NULL,
    order_no      VARCHAR(32)  NOT NULL,
    passenger_id  VARCHAR(32)  NOT NULL,
    instance_id   VARCHAR(32)  NOT NULL,
    cabin_class   ENUM('经济舱','头等舱') NOT NULL,
    fare_type     ENUM('标准','特价')     NOT NULL DEFAULT '标准',
    actual_price    DECIMAL(10,2) NOT NULL,
    fuel_infra_fee  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    status          ENUM('有效','已退','已改签作废','已使用')
                    NOT NULL DEFAULT '有效',
    PRIMARY KEY (ticket_no),
    KEY idx_ticket_order (order_no),
    KEY idx_ticket_passenger (passenger_id),
    KEY idx_ticket_instance_status (instance_id, status),
    CONSTRAINT fk_ticket_order FOREIGN KEY (order_no)
        REFERENCES aptorder(order_no),
    CONSTRAINT fk_ticket_passenger FOREIGN KEY (passenger_id)
        REFERENCES passenger(id_no),
    CONSTRAINT fk_ticket_cabinprice FOREIGN KEY (instance_id, cabin_class, fare_type)
        REFERENCES cabin_price(instance_id, cabin_class, fare_type),
    CONSTRAINT chk_ticket_price CHECK (actual_price >= 0),
    CONSTRAINT chk_ticket_fuel_fee CHECK (fuel_infra_fee >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE refund_change (
    refund_id      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ticket_no      VARCHAR(32)     NOT NULL,
    op_type        ENUM('退票','改签') NOT NULL,
    fee            DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    new_ticket_no  VARCHAR(32)     DEFAULT NULL,
    price_diff     DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    op_time        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (refund_id),
    KEY idx_refund_ticket (ticket_no),
    KEY idx_refund_optime (op_time DESC),
    CONSTRAINT fk_rc_ticket FOREIGN KEY (ticket_no)
        REFERENCES ticket(ticket_no),
    CONSTRAINT fk_rc_new_ticket FOREIGN KEY (new_ticket_no)
        REFERENCES ticket(ticket_no),
    CONSTRAINT chk_rc_fee CHECK (fee >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 管理员 ----------

CREATE TABLE admin (
    admin_id        VARCHAR(32)  NOT NULL,
    admin_password  VARCHAR(255) NOT NULL,
    admin_name      VARCHAR(64)  NOT NULL,
    PRIMARY KEY (admin_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------- 视图 ----------

CREATE OR REPLACE VIEW v_flight_search AS
SELECT
    fi.instance_id,
    fi.flight_no,
    fi.flight_date,
    fi.status AS instance_status,
    f.scheduled_departure,
    f.scheduled_arrival,
    f.fuel_infra_fee,
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

CREATE OR REPLACE VIEW v_order_summary AS
SELECT
    o.order_no,
    o.user_id,
    u.name AS user_name,
    o.total_amount,
    o.status,
    o.created_at,
    COUNT(t.ticket_no) AS ticket_count,
    SUM(CASE WHEN t.status = '有效' THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN t.status = '已退' THEN 1 ELSE 0 END) AS refunded_count
FROM aptorder o
JOIN user u ON o.user_id = u.user_id
LEFT JOIN ticket t ON o.order_no = t.order_no
GROUP BY o.order_no, o.user_id, u.name, o.total_amount, o.status, o.created_at;
