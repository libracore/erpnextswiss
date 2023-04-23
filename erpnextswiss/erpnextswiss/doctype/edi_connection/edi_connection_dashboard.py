from frappe import _

def get_data():
   return {
      'fieldname': 'edi_connection',
      'transactions': [
         {
            'label': _('Files'),
            'items': ['EDI File']
         }
      ]
   }
