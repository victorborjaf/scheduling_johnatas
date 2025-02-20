import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, add_to_date

class Appointment(Document):
    def before_validate(self):
        # Define o end_date com base no start_date e duration antes da validação.
        self.set_end_date()

    def before_save(self):
        # Garante que o end_date esteja definido antes de salvar.
        self.set_end_date()
        
    def before_insert(self):
        # Garante que o end_date esteja definido antes de inserir.
        self.set_end_date()
    
    def after_insert(self):
        """Envia notificação por e-mail após a criação do compromisso."""
        self.send_email_notification("Novo Compromisso Agendado")
        
    def on_update(self):
        """Envia notificação por e-mail após a atualização do compromisso."""
        self.send_email_notification("Compromisso Atualizado")

    def on_cancel(self):
        """Envia notificação por e-mail após o cancelamento do compromisso."""
        self.send_email_notification("Compromisso Cancelado")
        
    def send_email_notification(self, subject):
        """Envia um e-mail de notificação."""
        if self.seller:
            # Obtém o endereço de e-mail do vendedor
            seller_email = frappe.db.get_value("User", self.seller, "email")

            if seller_email:
                # Renderiza o template de e-mail
                email_template = frappe.get_doc("Email Template", "Appointment Notification")
                message = frappe.render_template(email_template.response, {"doc": self})

                # Envia o e-mail
                frappe.sendmail(
                    recipients=[seller_email],
                    subject=subject,
                    message=message,
                    reference_doctype=self.doctype,
                    reference_name=self.name
                )    
        
    
    def set_end_date(self):
        #Calcula e define o end_date com base no start_date e duration.
        if self.start_date and self.duration:
            # Converte start_date para um objeto datetime
            start_datetime = get_datetime(self.start_date)

            # Converte duration para um objeto timedelta
            
            duration_parts = str(self.duration).replace(".", ":").split(":")
            hours = int(duration_parts[0])
            minutes = int(duration_parts[1])
            seconds = int(duration_parts[2])

            # Calcula o end_date
            self.end_date = add_to_date(start_datetime, hours=hours, minutes=minutes, seconds=seconds)
        else:
            frappe.throw("start_date e duration são obrigatórios para calcular o end_date.", frappe.MandatoryError)
            
    def validate(self):
        """Valida se o vendedor já tem um compromisso no mesmo horário."""
        self.validate_seller_availability()

    def validate_seller_availability(self):
        """Verifica se o vendedor já tem um compromisso no mesmo horário."""
        if self.seller and self.start_date and self.end_date:
            # Converte as datas para objetos datetime
            start_datetime = get_datetime(self.start_date)
            end_datetime = get_datetime(self.end_date)

            # Consulta para verificar conflitos de horário
            conflicting_appointments = frappe.get_all(
                "Appointment",
                filters={
                    "seller": self.seller,
                    "end_date": [">", start_datetime],
                    "start_date": ["<", end_datetime],
                    "status": ["=", "Scheduled"],
                    "name": ["!=", self.name]  # Ignora o próprio documento durante a edição
                },
                fields=["name", "start_date", "end_date"]
            )
            
            if conflicting_appointments:
                start_date_br = conflicting_appointments[0].start_date.strftime("%d/%m/%Y %H:%M:%S")
                end_date_br = conflicting_appointments[0].end_date.strftime("%d/%m/%Y %H:%M:%S")
                frappe.throw(
                    f"""O vendedor {self.seller} já tem um compromisso no mesmo horário: 
                    {conflicting_appointments[0].name} (de {start_date_br} 
                    a {end_date_br}).""", frappe.ValidationError
                )
                
                
@frappe.whitelist()
def get_events(start, end, filters=None):
    """Retorna os eventos do calendário."""
    if not filters:
        filters = {}

    events = frappe.get_all(
        "Appointment",
        filters=[
            ["start_date", ">=", start],
            ["end_date", "<=", end]
        ],
        fields=["name", "client_name", "start_date", "end_date", "status", "seller"]
    )

    for event in events:
        if not event.get("end_date"):
            event["end_date"] = add_to_date(event["start_date"], minutes=60)
        event.update({
            "title": f"{event.client_name} ({event.seller})",
            "start": event.start_date,
            "end": event.end_date,
            "color": get_event_color(event.status)
        })
    return events

def get_event_color(status):
    """Retorna a cor do evento com base no status."""
    color_map = {
        "Scheduled": "#98d85b",  # Verde
        "Finished": "#5b8ff7",   # Azul
        "Canceled": "#ff6b6b"    # Vermelho
    }
    return color_map.get(status, "#cccccc")  # Cor padrão (cinza)