CREATE VIEW `viewVAT_405` AS
SELECT 
	`tabPurchase Invoice`.`posting_date` AS `posting_date`, 
    `tabPurchase Invoice`.`name` AS `name`, 
    `tabPurchase Invoice`.`base_grand_total`  AS `base_grand_total`, 
    `tabPurchase Invoice`.`taxes_and_charges` AS `taxes_and_charges`, 
    `tabPurchase Invoice`.`total_taxes_and_charges` AS `total_taxes_and_charges`
FROM `tabPurchase Invoice` 
WHERE `docstatus` = 1 AND `taxes_and_charges` LIKE '%405%'
UNION SELECT 
	`tabExpense Claim`.`posting_date` AS `posting_date`, 
    `tabExpense Claim`.`name` AS `name`, 
    `tabExpense Claim`.`total_claimed_amount`  AS `base_grand_total`, 
    `tabExpense Claim`.`taxes_and_charges` AS `taxes_and_charges`, 
    `tabExpense Claim`.`total_taxes_and_charges` AS `total_taxes_and_charges`
FROM `tabExpense Claim`
WHERE `docstatus` = 1 AND `taxes_and_charges` LIKE '%405%'