# erpnextswiss
ERPNext application for Switzerland-specific use cases

ERPNext ([https://www.erpnext.org](https://www.erpnext.org)) is a global, leading, cloud based
open source enterprise resource planning software. ERPNext is a trademark by Frappé Technologies.

The ERPNextSwiss application adds country-specific features to this platform such as 
bank, tax and payment integrations.

For more information, refer to [https://erpnext.swiss](https://erpnext.swiss)

## License 
GNU Affero General Public License, refer to LICENSE

ERPNextSwiss is developed and maintained by libracore and contributors. 
The copyright is owned by libracore and contributors. 
The software comes as-is without any warranty.

## Requirements
Requires an ERPNext server instance (refer to [https://github.com/frappe/erpnext](https://github.com/frappe/erpnext))

## Installation
From the frappe-bench folder, execute

    $ bench get-app https://github.com/libracore/erpnextswiss.git
    $ bench install-app erpnextswiss

## Update
Run updates with

    $ bench update

In case you update from the sources and observe an error, make sure to update dependencies with

    $ bench update --requirements

## Features 
* Banking
    * Bank import: allows to import bank account statements to update local payment entries (receiving)
    * Match payments: match unpaid sales invoices with the corresponding payments
    * Payment export: allows to create payment files for banks (pain.001) from payment entries (paying)
    * support for QR and ESR invoices
* Tax
    * Import monthly average exchange rates
    * VAT declaration
* Human resources
    * Salary certificate ("Lohnausweis")
* General tools
    * Postal code lookup
    * Script-based data import
    * Large data import tools

## Release notes
Refer to [https://github.com/libracore/erpnextswiss/wiki/Release-Notes](https://github.com/libracore/erpnextswiss/wiki/Release-Notes)
