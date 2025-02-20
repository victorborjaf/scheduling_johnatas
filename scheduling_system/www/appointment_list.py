import frappe

def get_context(context):
    context.appointments = frappe.get_all(
        "Appointment",
        fields=["client_name", "start_date", "status"]
    )
