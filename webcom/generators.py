import random
import re
from datetime import timedelta

from django.utils import timezone
from djmoney.money import Money
from faker import Faker

from webcom import models
from webcom.models import Customer, TechnicalEmployee


class Factory:

    def __init__(self):
        self.fake = Faker("en_US")

    def generate_address(self):
        street = self.fake.street_address()
        postal_code = self.fake.postcode()
        city = self.fake.city()
        return models.Address.objects.create(street=street, city=city, postal_code=postal_code)

    def generate_account(self):
        number = self.fake.credit_card_number()
        balance = Money(random.randint(0, 1000))
        return models.Account(number=number, balance=balance)

    def generate_regular_contract(self, expirable=True):
        approval_date = timezone.localtime(timezone.now())
        termination_date = approval_date + timedelta(days=random.randint(100, 720))
        termination_delay = random.choice((14, 30))
        if expirable:
            contract = models.RegularContract(approval_date=approval_date,
                                       termination_date=termination_date,
                                       termination_delay=termination_delay)
        else:
            contract = models.RegularContract(approval_date=approval_date,
                                       termination_delay=termination_delay)
        return contract

    def generate_business_contract(self, expirable=True):
        approval_date = timezone.localtime(timezone.now())
        termination_date = approval_date + timedelta(days=random.randint(100, 720))
        termination_delay = random.choice((30, 100))
        if expirable:
            contract = models.BusinessContract(approval_date=approval_date,
                                       termination_date=termination_date,
                                       termination_delay=termination_delay)
        else:
            contract = models.BusinessContract(approval_date=approval_date,
                                       termination_delay=termination_delay)
        return contract

    def generate_individual_customer(self, address=None):
        # Person stuff
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        apartment_number = str(random.randint(100, 999))
        n_address = address if address else self.generate_address()
        # Customer stuff
        account = self.generate_account()
        contract = self.generate_regular_contract(expirable=random.choice((True,False)))
        email = self.fake.email()
        phone_number = re.sub(r"(\s|-|\(|\))", "", self.fake.phone_number())
        return Customer.create(customer_type=Customer.REGULAR,
                               contract=contract,
                               account=account,
                               first_name=first_name,
                               last_name=last_name,
                               apartment_number=apartment_number,
                               address=n_address,
                               email=email,
                               phone_number=phone_number)

    def generate_business_customer(self):
        # Business customer stuff
        company_name = self.fake.company()
        company_id = self.fake.ean(length=13)
        # Customer stuff
        account = self.generate_account()
        contract = self.generate_business_contract(expirable=random.choice((True,False)))
        email = self.fake.email()
        phone_number = re.sub(r"(\s|-|\(|\))", "", self.fake.phone_number())
        return Customer.create(customer_type=Customer.BUSINESS,
                               contract=contract,
                               account=account,
                               company_name=company_name,
                               company_id=company_id,
                               email=email,
                               phone_number=phone_number)

    def generate_technical_employee(self, address=None, employee_type=None):
        # Person stuff
        first_name = self.fake.first_name()
        last_name = self.fake.last_name()
        apartment_number = str(random.randint(100, 999))
        n_address = address if address else self.generate_address()
        # Employee stuff
        salary = Money(random.choice((1000, 2500, 4500, 5000)), "USD")
        seniority = random.randint(1, 10)
        email = self.fake.email()
        phone_number = re.sub(r"(\s|-|\(|\))", "", self.fake.phone_number())
        employee_type = employee_type if employee_type else random.choice((TechnicalEmployee.TECHNICIAN, TechnicalEmployee.SYSADMIN))
        return TechnicalEmployee.create(type=employee_type,
                                        email=email,
                                        phone_number=phone_number,
                                        first_name=first_name,
                                        last_name=last_name,
                                        apartment_number=apartment_number,
                                        address=n_address,
                                        salary=salary,
                                        seniority=seniority)
