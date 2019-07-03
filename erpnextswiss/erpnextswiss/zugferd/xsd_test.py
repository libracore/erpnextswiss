# -*- coding: utf-8 -*-
from pprint import pprint
import xmlschema
import json
from collections import OrderedDict

# read the schema file
my_schema = xmlschema.XMLSchema('zugferd2p0_en16931.xsd')

# validate a file against the schema
print("Valid: {0}".format(my_schema.is_valid('zugferd_einfach.xml')))

# decode the file
content = my_schema.to_dict('zugferd_einfach.xml')
pprint(content)


# encode a dict
data = OrderedDict({
    u'@xmlns:a': 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100',
    u'@xmlns:ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
    u'@xmlns:rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100',
    u'@xmlns:udt': 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100',
    u'@xmlns:xs': 'http://www.w3.org/2001/XMLSchema',
    u'rsm:ExchangedDocument': {
        u'ram:ID': u'471102',
        u'ram:IncludedNote': [
            {
                u'ram:Content': u'Rechnung gem\xe4\xdf Bestellung vom 01.03.2018.'
            }, 
            {
                u'ram:Content': u'Lieferant GmbH\t\t\t\t\nLieferantenstra\xdfe 20\t\t\t\t\n80333 M\xfcnchen\t\t\t\t\nDeutschland\t\t\t\t\nGesch\xe4ftsf\xfchrer: Hans Muster\nHandelsregisternummer: H A 123\n      '
                #, u'ram:SubjectCode': u'REG'
            }
        ],
        u'ram:IssueDateTime': {
            u'udt:DateTimeString': {
                u'$': u'20180305',
                u'@format': u'102'
            }
        },
        u'ram:TypeCode': u'380'
    },
    u'rsm:ExchangedDocumentContext': {
        u'ram:GuidelineSpecifiedDocumentContextParameter': {
            u'ram:ID': u'urn:cen.eu:en16931:2017'
        }
    },
    u'rsm:SupplyChainTradeTransaction': {
        u'ram:ApplicableHeaderTradeAgreement': {
            u'ram:BuyerTradeParty': {
                u'ram:GlobalID': [
                    {
                        u'$': u'4000001987658',
                        u'@schemeID': u'0088'
                    }
                ],
                u'ram:ID': u'GE2020211',
                u'ram:Name': u'Kunden AG Mitte',
                u'ram:PostalTradeAddress': {
                    u'ram:CityName': u'Frankfurt',
                    u'ram:CountryID': u'DE',
                    u'ram:LineOne': u'Kundenstra\xdfe 15',
                    u'ram:PostcodeCode': u'69876'
                }
            },
            u'ram:SellerTradeParty': {
                u'ram:GlobalID': [
                    {
                        u'$': u'4000001123452',
                        u'@schemeID': u'0088'
                    }
                ],
                u'ram:Name': u'Lieferant GmbH',
                u'ram:PostalTradeAddress': {
                    u'ram:CityName': u'M\xfcnchen',
                    u'ram:CountryID': u'DE',
                    u'ram:LineOne': u'Lieferantenstra\xdfe 20',
                    u'ram:PostcodeCode': u'80333'
                },
                u'ram:SpecifiedTaxRegistration': [
                    {
                        u'ram:ID': {
                            u'$': u'201/113/40209',
                            u'@schemeID': u'FC'
                        }
                    }, {
                        u'ram:ID': {
                            u'$': u'DE123456789',
                            u'@schemeID': u'VA'
                        }
                    }
                ]
            }
        },
        u'ram:ApplicableHeaderTradeDelivery': {
            u'ram:ActualDeliverySupplyChainEvent': {
                u'ram:OccurrenceDateTime': {
                    u'udt:DateTimeString': {
                        u'$': u'20180305',
                        u'@format': u'102'
                    }
                }
            }
        },
        u'ram:ApplicableHeaderTradeSettlement': {
            u'ram:ApplicableTradeTax': [
                {
                    u'ram:BasisAmount': 275.00,
                    u'ram:CalculatedAmount': 19.25,
                    u'ram:CategoryCode': u'S',
                    u'ram:RateApplicablePercent': 7.00,
                    u'ram:TypeCode': u'VAT'
                }, {
                    u'ram:BasisAmount': 198.00,
                    u'ram:CalculatedAmount': 37.62,
                    u'ram:CategoryCode': u'S',
                    u'ram:RateApplicablePercent': 19.00,
                    u'ram:TypeCode': u'VAT'
                }
            ],
            u'ram:InvoiceCurrencyCode': u'EUR',
            u'ram:SpecifiedTradePaymentTerms': {
                u'ram:Description': u'Zahlbar innerhalb 30 Tagen netto bis 04.04.2018, 3% Skonto innerhalb 10 Tagen bis 15.03.2018'
            },
            u'ram:SpecifiedTradeSettlementHeaderMonetarySummation': {
                u'ram:AllowanceTotalAmount': 0.00,
                u'ram:ChargeTotalAmount': 0.00,
                u'ram:DuePayableAmount': 529.87,
                u'ram:GrandTotalAmount': 529.87,
                u'ram:LineTotalAmount': 473.00,
                u'ram:TaxBasisTotalAmount': 473.00,
                u'ram:TaxTotalAmount': {
                    u'$': 56.87,
                    u'@currencyID': u'EUR'
                },
                u'ram:TotalPrepaidAmount': 0.00
            }
        },
        u'ram:IncludedSupplyChainTradeLineItem': [
            {
                u'ram:AssociatedDocumentLineDocument': {
                    u'ram:LineID': u'1'
                },
                u'ram:SpecifiedLineTradeAgreement': {
                    u'ram:GrossPriceProductTradePrice': {
                        u'ram:ChargeAmount': 9.9000
                    },
                    u'ram:NetPriceProductTradePrice': {
                        u'ram:ChargeAmount': 9.9000
                    }
                },
                u'ram:SpecifiedLineTradeDelivery': {
                    u'ram:BilledQuantity': {
                        u'$': 20.0000,
                        u'@unitCode': u'C62'
                    }
                },
                u'ram:SpecifiedLineTradeSettlement': {
                    u'ram:ApplicableTradeTax': {
                        u'ram:CategoryCode': u'S',
                        u'ram:RateApplicablePercent': 19.00,
                        u'ram:TypeCode': u'VAT'
                    },
                    u'ram:SpecifiedTradeSettlementLineMonetarySummation': {
                        u'ram:LineTotalAmount': 198.00
                    }
                },
                u'ram:SpecifiedTradeProduct': {
                    u'ram:GlobalID': {
                        u'$': u'4012345001235',
                        u'@schemeID': u'0160'
                    },
                    u'ram:Name': u'Trennbl\xe4tter A4',
                    u'ram:SellerAssignedID': u'TB100A4'
                }
            },
            {
                u'ram:AssociatedDocumentLineDocument': {
                    u'ram:LineID': u'2'
                },
                u'ram:SpecifiedLineTradeAgreement': {
                    u'ram:GrossPriceProductTradePrice': {
                        u'ram:ChargeAmount': 5.5000
                    },
                    u'ram:NetPriceProductTradePrice': {
                        u'ram:ChargeAmount': 5.5000
                    }
                },
                u'ram:SpecifiedLineTradeDelivery': {
                    u'ram:BilledQuantity': {
                        u'$': 50.0000,
                        u'@unitCode': u'C62'
                    }
                },
                u'ram:SpecifiedLineTradeSettlement': {
                    u'ram:ApplicableTradeTax': {
                        u'ram:CategoryCode': u'S',
                        u'ram:RateApplicablePercent': 7.00,
                        u'ram:TypeCode': u'VAT'
                    },
                    u'ram:SpecifiedTradeSettlementLineMonetarySummation': {
                        u'ram:LineTotalAmount': 275.00
                    }
                },
                u'ram:SpecifiedTradeProduct': {
                    u'ram:GlobalID': {
                        u'$': u'4000050986428',
                        u'@schemeID': u'0160'
                    },
                    u'ram:Name': u'Joghurt Banane',
                    u'ram:SellerAssignedID': u'ARNR2'
                }
            }
        ]
    }
})

data_json = json.dumps(data)
print(data_json)
#print(xmlschema.from_json(source=data_json, schema=my_schema)) # does not work as ordering is ignored
