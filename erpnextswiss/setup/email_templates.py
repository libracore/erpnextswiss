import frappe


GERMAN_EMAIL_TEMPLATES = {
    "Exit Questionnaire Notification": {
        "subject": "Austrittsfragebogen",
        "response": """<h2>Austrittsfragebogen</h2>
<br>

<p>
	Guten Tag {{ employee_name }},
	<br><br>

	vielen Dank fuer Ihren Einsatz waehrend Ihrer Zeit bei {{ company }}.
	Ihre Rueckmeldung ist fuer uns wertvoll und hilft uns, uns weiter zu verbessern.
	Bitte nehmen Sie sich ein paar Minuten Zeit und fuellen Sie den Austrittsfragebogen aus.
	{% set web_form = frappe.db.get_single_value('HR Settings', 'exit_questionnaire_web_form') %}
	{% set web_form_link = frappe.utils.get_url(uri=frappe.db.get_value('Web Form', web_form, 'route')) %}

	<br><br>
	<a class="btn btn-primary" href="{{ web_form_link }}" target="_blank">Jetzt ausfuellen</a>
</p>
""",
    },
    "Interview Feedback Reminder": {
        "subject": "Erinnerung Interview-Feedback",
        "response": """<h1>Erinnerung Interview-Feedback</h1>

<p>
	Fuer das Interview {{ name }} wurde das Feedback noch nicht eingereicht.
	Bitte erfassen Sie Ihre Rueckmeldung. Vielen Dank.
</p>
""",
    },
    "Interview Reminder": {
        "subject": "Interview-Erinnerung",
        "response": """<h1>Interview-Erinnerung</h1>

<p>
	Das Interview {{ name }} ist am {{ scheduled_on }} von {{ from_time }} bis {{ to_time }} geplant.
</p>
""",
    },
    "Leave Status Notification": {
        "subject": "Status Ihres Abwesenheitsantrags",
        "response": """<h1>Status zum Abwesenheitsantrag</h1>
<h3>Details:</h3>

	<table class="table table-bordered small" style="max-width: 500px;">
		<tr>
			<td>Mitarbeitende Person</td>
			<td>{{ employee_name }}</td>
		</tr>
		<tr>
			<td>Abwesenheitsart</td>
			<td>{{ leave_type }}</td>
		</tr>
		<tr>
			<td>Von</td>
			<td>{{ from_date }}</td>
		</tr>
		<tr>
			<td>Bis</td>
			<td>{{ to_date }}</td>
		</tr>
		<tr>
			<td>Status</td>
			<td>{{ status }}</td>
		</tr>
	</table>

	{% set doc_link = frappe.utils.get_url_to_form('Leave Application', name) %}

	<br><br>
	<a class="btn btn-primary" href="{{ doc_link }}" target="_blank">Jetzt oeffnen</a>""",
    },
    "Leave Approval Notification": {
        "subject": "Neuer Abwesenheitsantrag zur Freigabe",
        "response": """<h1>Abwesenheitsantrag zur Freigabe</h1>
<h3>Details:</h3>

	<table class="table table-bordered small" style="max-width: 500px;">
		<tr>
			<td>Mitarbeitende Person</td>
			<td>{{ employee_name }}</td>
		</tr>
		<tr>
			<td>Abwesenheitsart</td>
			<td>{{ leave_type }}</td>
		</tr>
		<tr>
			<td>Von</td>
			<td>{{ from_date }}</td>
		</tr>
		<tr>
			<td>Bis</td>
			<td>{{ to_date }}</td>
		</tr>
		<tr>
			<td>Status</td>
			<td>{{ status }}</td>
		</tr>
	</table>

	{% set doc_link = frappe.utils.get_url_to_form('Leave Application', name) %}

	<br><br>
	<a class="btn btn-primary" href="{{ doc_link }}" target="_blank">Jetzt oeffnen</a>""",
    },
    "Dispatch Notification": {
        "subject": "Ihre Lieferung ist unterwegs",
        "response": """<h1>Versandbenachrichtigung</h1>
<h3>Details:</h3>
<table class="table table-bordered small" style="max-width:500px">
    <tbody>
        <tr>
            <td>Kunde</td>
            <td>{{ customer }}</td>
        </tr>
        <tr>
            <td>Kontaktperson</td>
            <td>{{ first_name }} {{ last_name }}</td>
        </tr>
        <tr>
            <td>Adressname</td>
            <td>{{ address }}</td>
        </tr>
        <tr>
            <td>Adressdetails</td>
            <td>{{ customer_address }}</td>
        </tr>
        <tr>
            <td>Lieferschein</td>
            <td>{{ delivery_note }}</td>
        </tr>
        <tr>
            <td>Gesamtsumme</td>
            <td>{{ grand_total }}</td>
        </tr>
        <tr>
            <td>Abfahrtszeit</td>
            <td>{{ departure_time }}</td>
        </tr>
        <tr>
            <td>Voraussichtliche Ankunft</td>
            <td>{{ estimated_arrival }}</td>
        </tr>
        <tr>
            <td>Fahrername</td>
            <td>{{ driver_name }}</td>
        </tr>
        <tr>
            <td>Telefon Fahrer</td>
            <td>{{ cell_number }}</td>
        </tr>
        <tr>
            <td>Fahrzeugnummer</td>
            <td>{{ vehicle }}</td>
        </tr>
    </tbody>
</table>
""",
    },
}


def sync_email_templates():
    if not frappe.db.exists("DocType", "Email Template"):
        return

    for template_name, values in GERMAN_EMAIL_TEMPLATES.items():
        desired = {
            "doctype": "Email Template",
            "name": template_name,
            "subject": values["subject"],
            "response": values["response"],
            "response_html": None,
            "use_html": 0,
        }

        if frappe.db.exists("Email Template", template_name):
            doc = frappe.get_doc("Email Template", template_name)
            changed = False
            for fieldname, value in desired.items():
                if fieldname == "doctype":
                    continue
                if doc.get(fieldname) != value:
                    doc.set(fieldname, value)
                    changed = True
            if changed:
                doc.save(ignore_permissions=True)
            continue

        frappe.get_doc(desired).insert(ignore_permissions=True)
