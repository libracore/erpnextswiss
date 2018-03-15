CREATE VIEW `viewVAT_200` AS
    SELECT 
        `tabSales Invoice`.`name` AS `name`,
        `tabSales Invoice`.`posting_date` AS `posting_date`,
        `tabSales Invoice`.`base_grand_total` AS `base_grand_total`
    FROM
        `tabSales Invoice`
    WHERE
        (`tabSales Invoice`.`docstatus` = 1)