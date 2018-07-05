CREATE VIEW `viewVAT_322` AS
    SELECT 
        `tabSales Invoice`.`posting_date` AS `posting_date`,
        `tabSales Invoice`.`name` AS `name`,
        `tabSales Invoice`.`base_grand_total` AS `base_grand_total`,
        `tabSales Invoice`.`taxes_and_charges` AS `taxes_and_charges`,
        `tabSales Invoice`.`total_taxes_and_charges` AS `total_taxes_and_charges`
    FROM
        `tabSales Invoice`
    WHERE
        ((`tabSales Invoice`.`docstatus` = 1)
            AND (`tabSales Invoice`.`taxes_and_charges` LIKE '%322%'))
