-- 将 fuel_infra_fee 固化进 ticket 表，避免航班燃油费变更后影响已支付订单的金额明细。
-- 先用 flight 表当前值回填已有数据，保证历史可追溯。

ALTER TABLE ticket
    ADD COLUMN fuel_infra_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00;

ALTER TABLE ticket
    ADD CONSTRAINT chk_ticket_fuel_fee CHECK (fuel_infra_fee >= 0);

-- 按现有航班燃油费回填已有的有效和已使用 ticket（已退/已改签作废的默认为 0）
UPDATE ticket t
JOIN flight_instance fi ON t.instance_id = fi.instance_id
JOIN flight f ON fi.flight_no = f.flight_no
SET t.fuel_infra_fee = f.fuel_infra_fee
WHERE t.fuel_infra_fee = 0.00;
