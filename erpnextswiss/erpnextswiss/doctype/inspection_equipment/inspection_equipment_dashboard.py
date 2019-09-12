from frappe import _

def get_data():
   return {
      'fieldname': 'inspection_equipment',
      'transactions': [
         {
            'label': _('Transaction'),
            'items': ['Inspection Equipment Transaction']
         },
		 {
            'label': _('Calibration / Test'),
            'items': ['Calibration Test']
         }
      ]
   }