# Copyright (c) 2025, johnatas and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from scheduling_system.scheduling_system.doctype.appointment.appointment import Appointment
import unittest
from frappe.utils import now_datetime, add_to_date


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class UnitTestAppointment(UnitTestCase):
	"""
	Unit tests for Appointment.
	Use this class for testing individual functions and methods.
	"""
	def setUp(self):
		"""Cria dados de teste antes de cada teste."""
		self.seller = "test_seller@example.com"
		self.client_name = "Test Client"
		self.start_date = now_datetime()
		self.duration = "01:00:00"  # 1 hora

		# Cria um usuário de teste (vendedor)
		if not frappe.db.exists("User", self.seller):
			user = frappe.get_doc({
				"doctype": "User",
				"email": self.seller,
				"first_name": "Test",
				"last_name": "Seller",
				"roles": [{"role": "System Manager"}]
			})
			user.insert()

	def tearDown(self):
		"""Limpa os dados de teste após cada teste."""
		frappe.db.rollback()

	def test_create_appointment(self):
		"""Testa a criação de um compromisso."""
		appointment = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": self.client_name,
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller
		})
		appointment.insert()

		# Verifica se o compromisso foi criado
		self.assertTrue(frappe.db.exists("Appointment", appointment.name))

		# Verifica se o end_date foi calculado corretamente
		expected_end_date = add_to_date(self.start_date, hours=1)
		self.assertEqual(appointment.end_date, expected_end_date)

	def test_validate_seller_availability(self):
		"""Testa a validação de conflitos de horário para o vendedor."""
		# Cria um compromisso inicial
		appointment1 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": self.client_name,
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		appointment1.insert()
  
		
		later_start = add_to_date(self.start_date, minutes=2)
  

		# Tenta criar um segundo compromisso no mesmo horário
		appointment2 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": "Another Client",
			"start_date": later_start,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})

		# Verifica se a validação de conflito é acionada
		with self.assertRaises(frappe.ValidationError):
			appointment2.insert()
   
	def test_validate_seller_availability_non_conflict(self):
		"""Testa a validação quando não há conflitos de horário."""
		# Cria o primeiro compromisso
		appointment1 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": self.client_name,
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		appointment1.insert()
		
		# Cria um segundo compromisso sem conflito (inicia 2 horas depois)
		later_start = add_to_date(self.start_date, hours=2)
		appointment2 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": "Non-conflicting Client",
			"start_date": later_start,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		# Chama a validação manualmente para verificar a ausência de conflito
		try:
			appointment2.insert()
		except Exception as e:
			self.fail(f"validate_seller_availability lançou exceção inesperada: {e}")
	
	def test_validate_seller_availability_ignore_non_scheduled(self):
		"""Testa que compromissos com status não 'Scheduled' não geram conflito."""
		# Cria um compromisso finalizado
		appointment1 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": self.client_name,
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Finished"  # Status diferente de 'Scheduled'
		})
		appointment1.insert()
		
		# Cria um compromisso com status 'Scheduled' no mesmo horário
		appointment2 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": "Another Client",
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		# Mesmo que os horários se sobreponham, appointment1 não deve acionar conflito
		try:
			appointment2.set_end_date()
			appointment2.validate_seller_availability()
		except Exception as e:
			self.fail(f"validate_seller_availability lançou exceção inesperada ao ignorar compromissos não 'Scheduled': {e}")


	def test_calendar_events(self):
		"""Testa a função que retorna eventos para o calendário."""
		# Cria um compromisso
		appointment = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": self.client_name,
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		appointment.insert()

		# Obtém os eventos do calendário
		events = frappe.get_attr("scheduling_system.scheduling_system.doctype.appointment.appointment.get_events")(
			start=self.start_date,
			end=add_to_date(self.start_date, hours=1)
		)

		# Verifica se o evento foi retornado corretamente
		self.assertEqual(len(events), 1)
		self.assertEqual(events[0]["title"], f"{self.client_name} ({self.seller})")
		self.assertEqual(events[0]["start"], self.start_date)
		self.assertEqual(events[0]["end"], appointment.end_date)
		self.assertEqual(events[0]["color"], "#98d85b")  # Cor para "Scheduled"

	# New test: appointment overlapping on the end (starts before existing and ends during)
	def test_overlap_end(self):
		appointment1 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": self.client_name,
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		appointment1.insert()
		overlap_start = add_to_date(self.start_date, minutes=-30)  # starts 30 mins earlier; ends at self.start_date + 30 mins
		appointment2 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": "Overlap End Client",
			"start_date": overlap_start,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		with self.assertRaises(frappe.ValidationError):
			appointment2.insert()

	# New test: appointment overlapping on the start (starts during existing and ends after)
	def test_overlap_start(self):
		appointment1 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": self.client_name,
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		appointment1.insert()
		overlap_start = add_to_date(self.start_date, minutes=30)  # starts 30 mins after; ends at self.start_date + 1h30
		appointment2 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": "Overlap Start Client",
			"start_date": overlap_start,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		with self.assertRaises(frappe.ValidationError):
			appointment2.insert()

	# New test: new appointment completely inside an existing scheduled appointment
	def test_appointment_inside(self):
		appointment1 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": self.client_name,
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		appointment1.insert()
		inside_start = add_to_date(self.start_date, minutes=15)  # Starts 15 mins after
		appointment2 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": "Inside Appointment Client",
			"start_date": inside_start,
			"duration": "00:30:00",  # Ends before appointment1 ends
			"seller": self.seller,
			"status": "Scheduled"
		})
		with self.assertRaises(frappe.ValidationError):
			appointment2.insert()

	# New test: new appointment surrounding an existing scheduled appointment
	def test_appointment_surrounding(self):
		appointment1 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": self.client_name,
			"start_date": self.start_date,
			"duration": self.duration,
			"seller": self.seller,
			"status": "Scheduled"
		})
		appointment1.insert()
		surround_start = add_to_date(self.start_date, minutes=-15)  # Starts 15 mins before
		appointment2 = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": "Surrounding Appointment Client",
			"start_date": surround_start,
			"duration": "01:30:00",  # Ends 15 mins after appointment1 ends
			"seller": self.seller,
			"status": "Scheduled"
		})
		with self.assertRaises(frappe.ValidationError):
			appointment2.insert()

class IntegrationTestAppointment(IntegrationTestCase):
	"""
	Integration tests for Appointment.
	Use this class for testing interactions between multiple components.
	"""

	def test_integration_create_and_get_events(self):
		seller = "test_integration_seller@example.com"
		# Cria usuário de teste se não existir
		if not frappe.db.exists("User", seller):
			user = frappe.get_doc({
				"doctype": "User",
				"email": seller,
				"first_name": "Integration",
				"last_name": "Seller",
				"roles": [{"role": "System Manager"}]
			})
			user.insert()
		
		# Cria um compromisso de integração
		appointment = frappe.get_doc({
			"doctype": "Appointment",
			"client_name": "Integration Client",
			"start_date": now_datetime(),
			"duration": "01:00:00",
			"seller": seller,
			"status": "Scheduled"
		})
		appointment.insert()
		
		# Obtém eventos do calendário
		events = frappe.get_attr("scheduling_system.scheduling_system.doctype.appointment.appointment.get_events")(
			start=appointment.start_date,
			end=appointment.end_date
		)
		
		# Verifica se o evento foi retornado corretamente
		self.assertTrue(len(events) > 0)
		expected_title = f"Integration Client ({seller})"
		self.assertEqual(events[0]["title"], expected_title)

