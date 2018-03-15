CREATE VIEW `viewVAT_235` AS
    SELECT 
        `tabGL Entry`.`posting_date` AS `posting_date`,
        `tabGL Entry`.`voucher_no` AS `voucher_no`,
        `tabGL Entry`.`account` AS `account`,
        `tabGL Entry`.`debit` AS `debit`,
        `tabGL Entry`.`credit` AS `credit`
    FROM
        `tabGL Entry`
    WHERE
        ((`tabGL Entry`.`docstatus` = 1)
            AND (`tabGL Entry`.`voucher_type` = 'Journal Entry')
            AND (`tabGL Entry`.`account` LIKE '%Delkredere%'))