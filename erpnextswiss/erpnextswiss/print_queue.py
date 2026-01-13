# Copyright (c) 2025, libracore and Contributors
# License: GNU General Public License v3. See license.txt
import time, socket, base64, io
import frappe
import traceback
from frappe import _
from frappe.utils import today, add_days
from frappe.utils.file_manager import save_file, get_file, remove_file_by_url
from PyPDF2 import PdfFileReader


@frappe.whitelist()
def print_doc_as_label(doctype, docname, label_printer, print_format=None):
    """
    Convert a document to a PDF and create a label printer job from it
    """
    pdf_bytes = frappe.get_print(doctype, docname, print_format, as_pdf=True)
    return pdf_to_print_job(pdf_bytes, label_printer)


def pdf_to_print_job(pdf_data, label_printer):
    file_doc = save_file(
        fname="print_job_.pdf",
        content=pdf_data,
        dt=None,
        dn=None,
        is_private=1
    )
    print_job = frappe.get_doc({
        "doctype": "Label Printer Job",
        "printer": label_printer,
        "pdf_file": file_doc.name,
    })
    print_job.insert()

    file_doc.attached_to_doctype = "Label Printer Job"
    file_doc.attached_to_name = print_job.name
    file_doc.attached_to_field = "pdf_file"
    file_doc.save()

    frappe.db.commit()
    return print_job.name


# Convert data of a print job to raw Bytes to send to the printer
# In case of PDF Direct Printing, determine print width of document and return a ZPL command to set the printer's width correctly before printing
def job_to_raw_bytes(print_job):
    job_doc = frappe.get_doc("Label Printer Job", print_job)
    label_printer = frappe.get_doc("Label Printer", job_doc.printer)

    if label_printer.accepted_input == "PDF files":
        if not job_doc.pdf_file:
            job_doc.status = "Failed"
            job_doc.status_message = "No PDF file attached"
            job_doc.save()
            return False
        job_data = get_file(job_doc.pdf_file)
        if isinstance(job_data, list) and len(job_data) == 2:
            job_data = job_data[1]
        if not isinstance(job_data, bytes):
            job_doc.status = "Failed"
            job_doc.status_message = "Unexpected attachment format (Bytes expected)"
            job_doc.save()
            return False

        # PDF direct printing (Zebra): Determine document width and set it using a printer command
        # (a workaround to ensure the printing width is always set correctly)
        pdf_stream = io.BytesIO(job_data)
        pdf_reader = PdfFileReader(pdf_stream)
        print_width = pdf_reader.pages[0].mediaBox.getWidth()*25.4/72 # Convert point to mm
        zebra_width = round(print_width*label_printer.pdf_direct_dpi/25.4) # Convert mm to Zebra-points
        pdf_stream.close()
        width_command = "! U1 setvar \"ezpl.print_width\" \"{width}\"\r\n".format(width=zebra_width).encode()
        return width_command + job_data

    elif label_printer.accepted_input == "Raw printer commands":
        job_data = job_doc.raw_data
        if isinstance(job_data, str):
            job_data = job_data.encode("utf-8")
        return job_data

    else:
        job_doc.status = "Failed"
        job_doc.status_message = "Unexpected value for 'accepted_input"
        job_doc.save()
        return


# Execute a print job by sending it directly to a label printer
def exec_direct_print_job(print_job):
    frappe.db.rollback() # Sync to any recent commits
    job_doc = frappe.get_doc("Label Printer Job", print_job)
    if job_doc.status != "Waiting":
        frappe.log_error(_("Unexpected job status: {0}").format(job_doc.status), _("Print job execution failed"))
        return
    label_printer = frappe.get_doc("Label Printer", job_doc.printer)
    if label_printer.printing_method != "Direct printing":
        frappe.db.update("Label Printer Job", print_job, {
            "status": "Failed",
            "status_message": "Invalid job for direct printing",
        })
        return

    # Obtain data from DB and/or PDF file
    job_bytes = job_to_raw_bytes(print_job)
    if not job_bytes:
        # Errors in job data are handled directly by the function
        return

    # Send data to printer
    try:
        frappe.db.set_value("Label Printer Job", print_job, "status", "Printing")
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = int(label_printer.printer_port) or 9100
        soc.connect((label_printer.printer_hostname, port))
        soc.sendall(job_bytes)
        soc.close()
        frappe.db.set_value("Label Printer Job", print_job, "status", "Printed")
    except Exception as e:
        frappe.db.update("Label Printer Job", print_job, {
            "status": "Failed",
            "status_message": traceback.format_exc(),
        })


LONG_POLL_SECONDS = 60
POLL_INTERVAL = 0.5

@frappe.whitelist(allow_guest=False)
def set_job_status(job_name, status, message=''):
    try:
        job_doc = frappe.get_doc("Label Printer Job", job_name)
    except frappe.DoesNotExistError:
        return
    if job_doc:
        job_doc.status = status
        job_doc.status_message = message
        job_doc.save()
        frappe.enqueue("erpnextswiss.erpnextswiss.print_queue.cleanup_print_queue")

@frappe.whitelist(allow_guest=False)
def get_group_jobs(group_name, limit=10):
    """
    Return up to `limit` waiting Label Printer Jobs for the Label Printer Group `group_name`.
    Atomically reserve returned jobs (set status='Printing').
    If no jobs are waiting, this will long-poll up to LONG_POLL_SECONDS and return either new jobs or timed_out=True.
    Response (frappe message): {"jobs": [...], "timed_out": bool}
    """
    start = time.time()
    limit = int(limit)

    if not frappe.db.exists("Label Printer Group", group_name):
        return {"jobs": [], "timed_out": True, "message": _("Group not found")}

    printers = frappe.get_all("Label Printer",
                              filters={"printer_group": group_name},
                              fields=["name"])
    printer_names = [p.name for p in printers]
    if not printer_names:
        return {"jobs": [], "timed_out": True, "message": _("No printers in group")}

    while True:
        jobs = _fetch_waiting_jobs_for_printers(printer_names, limit)
        if jobs:
            return {"jobs": jobs, "timed_out": False}
        if time.time() - start >= LONG_POLL_SECONDS:
            return {"jobs": [], "timed_out": True}
        time.sleep(POLL_INTERVAL)


def _fetch_waiting_jobs_for_printers(printer_names, limit):
    frappe.db.rollback() # Sync to any recent commits
    waiting_jobs = frappe.get_all(
        "Label Printer Job",
        filters=[
            ["printer", "in", printer_names],
            ["status", "=", "Waiting"]
        ],
        fields=["name", "printer", "raw_data", "pdf_file"],
        order_by="creation asc",
        limit_page_length=limit
    )

    useful_jobs = []
    for job in waiting_jobs:
        printer_doc = frappe.get_doc("Label Printer", job['printer'])
        # Ignore printers with direct printing
        if printer_doc.printing_method != 'Via client script':
            continue
        try:
            job['printer_hostname'] = printer_doc.printer_hostname
            job['printer_port'] = printer_doc.printer_port
            job_bytes = job_to_raw_bytes(job['name'])
            if not job_bytes:
                # Job status is set to Failed by job_to_raw_bytes() in such cases
                continue
            job['data_base64'] = base64.b64encode(job_bytes).decode('ascii')
        except Exception as e:
            frappe.db.update("Label Printer Job", job['name'], {
                "status": "Failed",
                "status_message": traceback.format_exc(),
            })
            continue

        useful_jobs.append(job)
        frappe.db.set_value("Label Printer Job", job['name'], "status", "Printing")

    return useful_jobs


def cleanup_print_queue():
    """
    Delete old print jobs
    """
    cutoff = add_days(today(), -1)
    jobs = frappe.get_all(
        "Label Printer Job",
        filters={
            "status": ["in", ["Printed", "Failed"]],
            "creation": ["<", cutoff],
        },
        fields=["name"],
    )

    for job in jobs:
        frappe.delete_doc("Label Printer Job", job['name'])
    frappe.db.commit()