frappe.views.calendar['Appointment'] = {
    field_map: {
        start: 'start_date',  // Campo de data de início
        end: 'end_date',      // Campo de data de término
        id: 'name',           // Campo de identificação única
        title: 'title', // Campo que será exibido como título no calendário
        status: 'status',     // Campo que define o status (opcional)
        color: 'color'        // Campo que define a cor (opcional)
    },
    style_map: {
        Scheduled: 'success', // Estilo para compromissos agendados
        Finished: 'info',     // Estilo para compromissos finalizados
        Canceled: 'danger'    // Estilo para compromissos cancelados
    },
    order_by: 'start_date',  // Ordena os eventos pela data de início
    get_events_method: 'scheduling_system.scheduling_system.doctype.appointment.appointment.get_events'  // Método para buscar eventos
};