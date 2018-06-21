from django.test import TestCase
from django.utils import timezone
from djmoney.money import Money

from webcom.generators import Factory
from webcom.models import \
    Address, \
    Account, BusinessContract, RegularContract, Customer, RegularCustomer, BusinessCustomer, TechnicalEmployee, \
    Technician, SysAdmin, Addendum, Service, Laptop, LaptopRepair, Server, ServerRepair, Router, RouterRepair


class IndividualCustomerTestCase(TestCase):

    def setUp(self):
        self.factory = Factory()

    def test_individual_customer(self):
        customer = self.factory.generate_individual_customer()

        customer.save()

        self.assertEqual(customer.account, Account.objects.first())
        self.assertEqual(customer.address, Address.objects.first())
        self.assertEqual(customer.contract, RegularContract.objects.first())
        self.assertEqual(customer.first_name, RegularCustomer.objects.first().first_name)

        customer.delete()

        self.assertEqual(0, Customer.get_regular_customers().count())
        self.assertEqual(0, Account.objects.count())
        self.assertEqual(0, RegularContract.objects.count())


class BusinessCustomerTestCase(TestCase):

    def setUp(self):
        self.factory = Factory()

    def test_business_customer(self):
        customer = self.factory.generate_business_customer()

        customer.save()

        self.assertEqual(customer.account, Account.objects.first())
        self.assertEqual(customer.contract, BusinessContract.objects.first())
        self.assertEqual(customer.company_name, BusinessCustomer.objects.first().company_name)

        customer.delete()

        self.assertEqual(0, Customer.get_business_customers().count())
        self.assertEqual(0, Account.objects.count())
        self.assertEqual(0, BusinessContract.objects.count())


class TechnicalEmployeeTestCase(TestCase):

    def setUp(self):
        self.factory = Factory()

    def test_technician_employee(self):
        technician = self.factory.generate_technical_employee(employee_type=TechnicalEmployee.TECHNICIAN)

        technician.save()

        self.assertEqual(technician.address, Address.objects.first())
        self.assertEqual(technician.instance, Technician.objects.first())
        self.assertEqual(technician.bonus, Money("0.0"))

        technician.delete()

        self.assertEqual(None, Technician.objects.first())

    def test_sysadmin_employee(self):
        sysadmin = self.factory.generate_technical_employee(employee_type=TechnicalEmployee.SYSADMIN)

        sysadmin.save()

        self.assertEqual(sysadmin.address, Address.objects.first())
        self.assertEqual(sysadmin.instance, SysAdmin.objects.first())
        self.assertEqual(sysadmin.bonus, sysadmin.salary*0.1)

        sysadmin.delete()

        self.assertEqual(None, SysAdmin.objects.first())

    def test_dynamic_context(self):
        tech_employee = self.factory.generate_technical_employee(employee_type=TechnicalEmployee.TECHNICIAN)

        tech_employee.save()

        self.assertEqual(tech_employee.bonus, Money("0.0"))

        tech_employee.instance = TechnicalEmployee.SYSADMIN

        tech_employee.save()

        self.assertEqual(None, Technician.objects.first())
        self.assertEqual(tech_employee.instance, SysAdmin.objects.first())

        self.assertEqual(tech_employee.bonus, tech_employee.salary * 0.1)

        tech_employee.instance = TechnicalEmployee.TECHNICIAN

        tech_employee.save()

        self.assertEqual(None, SysAdmin.objects.first())
        self.assertEqual(tech_employee.instance, Technician.objects.first())


class AddendumTestCase(TestCase):

    def setUp(self):
        self.factory = Factory()

    def test_addendum(self):

        customer = self.factory.generate_individual_customer()
        customer.save()

        s1 = Service.objects.create(name="Service 1")
        s2 = Service.objects.create(name="Service 2")
        s3 = Service.objects.create(name="Service 3")

        addendum = Addendum.objects.create(datetime_created=timezone.localtime(timezone.now()))
        addendum.services.add(s1)
        addendum.services.add(s2)
        addendum.services.add(s3)
        addendum.save()
        customer.contract.addendums.add(addendum)
        customer.save()

        self.assertEqual(RegularContract.objects.first().current_addendum, addendum)
        self.assertEqual(RegularContract.objects.first().addendums.first().services.count(), 3)


class ServiceTestCase(TestCase):

    def setUp(self):
        self.factory = Factory()

    def test_service(self):
        service = Service(name="Service Test",price=Money("20.00"))
        service.save()

    def test_recursive_association(self):
        s1 = Service.objects.create(name="Service containing services", price=Money("10.00"))

        s1.included.add(s1)

        with self.assertRaises(ValueError):
            s1.clean()

    def test_inclusion_association(self):

        s2 = Service.objects.create(name="Service Test 2", price=Money("10.00"))
        s3 = Service.objects.create(name="Service Test 3", price=Money("10.00"))
        s4 = Service.objects.create(name="Service Test 4", price=Money("10.00"))
        s5 = Service.objects.create(name="Service Test 5", price=Money("10.00"))
        s6 = Service.objects.create(name="Service Test 6", price=Money("10.00"))

        s2.included.add(s3, s4, s5, s6)

        with self.assertRaises(ValueError):
            s2.clean()

        s2.included.remove(s4, s5, s6)

        s4.included.add(s5, s6)

        s2.included.add(s4)

        with self.assertRaises(ValueError):
            s2.clean()

        s2.included.clear()

        s2.included.add(s5,s5)

        s2.save()

        self.assertEqual(1,s2.included.count())


class RepairTestCase(TestCase):

    def setUp(self):
        self.factory = Factory()

    def test_laptop_repair(self):

        technician = self.factory.generate_technical_employee(employee_type=TechnicalEmployee.TECHNICIAN)

        technician.save()

        laptop = Laptop.objects.create(manufacturer="HP",model="x360")

        repair = LaptopRepair(datetime_repaired=timezone.localtime(timezone.now()),
                              technician=technician.instance,
                              laptop=laptop)

        repair.save()

        LaptopRepair.objects.create(datetime_repaired=timezone.localtime(timezone.now()),
                                    technician=technician.instance,
                                    laptop=laptop)

        self.assertEqual(2, LaptopRepair.objects.count())

    def test_server_repair(self):

        technician = self.factory.generate_technical_employee(employee_type=TechnicalEmployee.TECHNICIAN)

        technician.save()

        server = Server.objects.create(manufacturer="HP",model="x360")

        repair = ServerRepair(datetime_repaired=timezone.localtime(timezone.now()),
                              technician=technician.instance,
                              server=server)

        repair.save()

        ServerRepair.objects.create(datetime_repaired=timezone.localtime(timezone.now()),
                                    technician=technician.instance,
                                    server=server)

        self.assertEqual(2, ServerRepair.objects.count())

    def test_router_repair(self):

        technician = self.factory.generate_technical_employee(employee_type=TechnicalEmployee.TECHNICIAN)

        technician.save()

        router = Router.objects.create(manufacturer="HP",model="x360")

        repair = RouterRepair(datetime_repaired=timezone.localtime(timezone.now()),
                              technician=technician.instance,
                              router=router)

        repair.save()

        RouterRepair.objects.create(datetime_repaired=timezone.localtime(timezone.now()),
                                    technician=technician.instance,
                                    router=router)

        self.assertEqual(2, RouterRepair.objects.count())











