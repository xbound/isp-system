from datetime import timedelta
from functools import reduce

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from djmoney.models.fields import MoneyField
from djmoney.money import Money


class Address(models.Model):
    """
    Model representing address data in the system.
    """
    # Required field street field of type str
    street = models.CharField(max_length=50, blank=False, null=False)
    # Required field city field of type str
    city = models.CharField(max_length=30, blank=False, null=False)
    # Required field postal_code field of type str
    postal_code = models.CharField(max_length=30, blank=False, null=False)

    def __str__(self):
        """
        To string method for Address object
        :return: str
        """
        return "{} {} {} {}".format(self.id, self.street, self.city, self.postal_code)


class Person(models.Model):
    """
    Abstract model for representing personal data of customers/employees.
    """
    # Required field first_name field :type str
    first_name = models.CharField(max_length=30, blank=False, null=False)
    # Required field last_name field :type str
    last_name = models.CharField(max_length=30, blank=False, null=False)
    # Required field apartment_number field :type str
    apartment_number = models.CharField(max_length=10, blank=False, null=False)
    # Foreign key to Address model
    # on_delete=models.PROTECT forbids deletion of Address object if it has
    # relation to object of Person type.
    address = models.ForeignKey("webcom.Address",
                                on_delete=models.PROTECT,
                                null=False)

    # Meta class for specifing properties of class
    class Meta:
        abstract = True


class ContactDataMixin(models.Model):
    """
    Abstract class for storing contact data of customers or employees.
    """
    # Required email field :type str
    email = models.EmailField(max_length=30, blank=False)
    # Validator for phone_number field
    phone_regex = RegexValidator(regex=r'^\+?\d{9,20}$',
                                 message=_("Phone number must be entered in the format: '+999999999'. Up to 20 digits allowed."))
    # Required field phone_number with phone_regex validator:type str
    phone_number = models.CharField(validators=[phone_regex], max_length=20, blank=False)

    # Meta class for specifing properties of class
    class Meta:
        abstract=True


class Customer(ContactDataMixin):
    """
    Model for representing customer data in the system, extends from ContactDataMixin
    """

    # Enum type REGULAR customer
    REGULAR = "REGULAR"
    # Enum type BUSINESS customer
    BUSINESS = "BUSINESS"

    choices = (
        (REGULAR,"Regular"),
        (BUSINESS, "Business")
    )

    # Required field for storing customer enum type
    type = models.CharField(max_length=10, choices=choices, blank=False)

    @classmethod
    def get_regular_customers(cls):
        """
        Class method for returning all regular customers in database.
        :return QuerySet<Customer|REGULAR>:
        """
        return cls.objects.filter(type=Customer.REGULAR).all()

    @classmethod
    def get_business_customers(cls):
        """
        Class method for returning all business customers in database.
        :return QuerySet<Customer|BUSINESS>:
        """
        return cls.objects.filter(type=Customer.BUSINESS).all()

    @classmethod
    def create(cls, customer_type, contract, account, email, phone_number, **kwargs):
        """

        :param customer_type: enum type Customer.REGULAR|Customer.BUSINESS
        :param contract: Contract object
        :param account: Account object
        :param email: str
        :param phone_number: str
        :param kwargs: other dictionary arguments
        :return: Customer
        """
        customer = cls(account=account, type=customer_type, email=email, phone_number=phone_number)
        if customer_type == Customer.REGULAR:
            customer.rc = RegularCustomer(**kwargs)
            customer.regularcontract = contract
        else:
            customer.bc = BusinessCustomer(**kwargs)
            customer.businesscontract = contract
        return customer

    @property
    def contract(self):
        """ Contract property :getter"""
        if self.type == Customer.REGULAR:
            return self.regularcontract
        else:
            return self.businesscontract

    @contract.setter
    def contract(self, contract):
        """ Contract property :setter"""
        if self.type == Customer.REGULAR:
            if not isinstance(contract, RegularContract):
                raise TypeError("Expected %s contract type..." % RegularContract.__name__)
            self.regularcontract = contract
        elif self.type == Customer.BUSINESS:
            if not isinstance(contract, BusinessContract):
                raise TypeError("Expected %s contract type..." % BusinessContract.__name__)
            self.businesscontract = contract
        else:
            raise AttributeError("Type of customer not set yet...")

    def save(self, *args,**kwargs):
        """
        Overridden save method for saving object to database.
        :param args: positional arguments
        :param kwargs: key dictionary arguments
        :return: None
        """
        super().save(*args, **kwargs)
        self.account = self.account
        self.account.save()
        self.contract = self.contract
        self.contract.save()
        if self.type == Customer.REGULAR:
            self.rc = self.rc
            self.rc.save()
        else:
            self.bc = self.bc
            self.bc.save()

    def delete(self, *args, **kwargs):
        """
        Overridden method for deleting Customer object from database.
        :param args: positional arguments
        :param kwargs: key dictionary arguments
        :return: Customer <deleted>
        """
        if self.account.balance.amount < Money("0.0").amount:
            raise ValueError("Cannot remove user due to debt...")
        self.account.delete()
        self.contract.delete()
        if self.type == Customer.REGULAR:
            self.rc.delete()
        else:
            self.bc.delete()
        return super().delete(*args, **kwargs)

    def __getattr__(self, item):
        """
        Method for delegating attribute calls to hooked RegularCustomer or BusinessCustomer
        :param item: attribute object
        :return: item called from RegularCustomer or BusinessCustomer context
        """
        if self.type == Customer.REGULAR:
            return getattr(self.rc, item)
        else:
            return getattr(self.bc, item)

    def __str__(self):
        """
        To string method.
        :return: str
        """
        if self.type == Customer.REGULAR:
            return "{} {} {}".format(self.rc.first_name,self.rc.last_name, self.type)
        return "{} {} {}".format(self.bc.company_name,self.bc.company_id, self.type)


class Account(models.Model):
    """
    Model for representing account data in the system.
    """
    # Reference to Customer model
    customer = models.OneToOneField("webcom.Customer", on_delete=models.CASCADE,
                                    to_field="id")
    # Required field number :type: str
    number = models.CharField(max_length=20, blank=False, null=True)
    # Field for representing amount of money on account
    balance = MoneyField(max_digits=10, decimal_places=2, null=False)

    def pay(self):
        """
        Withdraw amount from account based on total price of services in contract's addendum.
        """
        prices = map(lambda s: s.total_price, self.customer.contract.current_addendum.services.all())
        amount = reduce(lambda summary, price: summary + price, prices)
        self.balance -= amount
        return amount

    def __str__(self):
        """
        To string method
        :return: str
        """
        return "Account of {} -> {} {}".format(str(self.customer),
                                               self.number,
                                               self.balance)


class RegularCustomer(Person):
    """
    Extension to Customer for creating regular customers in database, extends from Person
    """
    # Reference to Customer base
    # When base is deleted extension daleted as well with on_delete=models.CASCADE constraint
    customer_base = models.OneToOneField("webcom.Customer",
                                         on_delete=models.CASCADE,
                                         related_name="rc")


class BusinessCustomer(models.Model):
    """
    Extension to Customer for creating business customers in database
    """
    # Reference to Customer base
    # When base is deleted extension daleted as well with on_delete=models.CASCADE constraint
    customer_base = models.OneToOneField("webcom.Customer",
                                         on_delete=models.CASCADE,
                                         related_name="bc")
    # Required field company_name :type: str
    company_name = models.CharField(max_length=50, blank=False, null=False)
    # Required field company_id :type: str
    company_id = models.CharField(max_length=50, blank=False, null=False, unique=True)


class Contract(models.Model):
    """
    Abstract model representing contract data in the system.
    """
    # Active enum type of Contract
    ACTIVE = "ACTIVE"
    # Suspended enum type of Contract
    SUSPENDED = "SUSPENDED"

    status_choices = (
        (ACTIVE,"ACTIVE"),
        (SUSPENDED,"SUSPENDED")
    )
    # EXPIRABLE enum type of Contract
    EXPIRABLE = "EXPIRABLE"
    # NONEXPIRABLE enum type of Contract
    NONEXPIRABLE = "NONEXPIRABLE"

    duration_choices = (
        (EXPIRABLE, "EXPIRABLE"),
        (NONEXPIRABLE, "NONEXPIRABLE")
    )

    # Required field duartion_type for storing type of Contract based on duration
    duration_type = models.CharField(max_length=12,
                                     choices=duration_choices,
                                     blank=False,
                                     default=EXPIRABLE)

    # Reference to Customer model
    customer = models.OneToOneField("webcom.Customer", on_delete=models.CASCADE)
    # Required field approval_date
    approval_date = models.DateTimeField(null=False)
    # Optional field termination_date
    termination_date = models.DateTimeField(null=True, blank=True)
    # Field for storing status state of Contract
    status = models.CharField(max_length=10, choices=status_choices, default=ACTIVE)

    # Meta class for specifing properties of class
    class Meta:
        abstract = True

    @property
    def duration(self):
        """
        Property :getter: for contract's duration.
        :return datetime.datetime:
        """
        if self.termination_date is not None:
            return self.termination_date - self.approval_date
        else:
            return timezone.now() + timedelta(days=100)

    def save(self, *args, **kwargs):
        """
        Overridden save method for saving object to database.
        :param args: positional arguments
        :param kwargs: key dictionary arguments
        :return: None
        """
        super().save(*args, **kwargs)

    @property
    def current_addendum(self):
        """
        Property :getter: returning current addendum of contract
        :return:
        """
        return self.addendums.latest(field_name="datetime_created")

    def __str__(self):
        """
        To string method
        :return: str
        """
        if self.customer.type == Customer.REGULAR:
            return "Contract of {} {} - {}".format(self.customer.first_name,
                                                   self.customer.last_name,
                                                   self.status)
        else:
            return "Contract of {} - {}".format(self.customer.company_name, self.status)


class RegularContract(Contract):
    """
    Model representing contract for regular customers in the system.
    """
    # Class attribute of termination_delay
    regular_contract_termination_delay = 10
    # Required model field of termination_delay :type: int
    termination_delay = models.PositiveSmallIntegerField(validators=[MinValueValidator(10)],
                                                         blank=False)
    # Required field of payment term :type: int
    pay_term = models.PositiveSmallIntegerField(default=30, blank=False)

    def __str__(self):
        """
        To string method
        :return: str
        """
        return "Contract of {} {} -> {} {}".format(self.approval_date,
                                                   self.status,
                                                   self.customer.first_name,
                                                   self.customer.last_name)


class BusinessContract(Contract):
    """
    Model representing contract for business customers in the system.
    """
    # Class attribute of termination_delay
    business_contract_termination_delay = 30
    # Required model field of termination_delay :type: int
    termination_delay = models.PositiveSmallIntegerField(validators=[MinValueValidator(30)],
                                                         blank=False)
    # Required field of payment term :type: int
    pay_term = models.PositiveSmallIntegerField(default=60, blank=False)

    def __str__(self):
        return "Contract:{} {} -> {}".format(self.approval_date,
                                             self.status,
                                             self.customer.company_name)


class Service(models.Model):
    """
    Model representing Service model in the system
    """
    # Required unique field representing service name :type: str
    name = models.CharField(max_length=30, blank=False, null=False, unique=True)
    # Required field representing service price :type: Money
    price = MoneyField(max_digits=10, decimal_places=2, blank=False, null=False)
    # Set of included Services
    included = models.ManyToManyField("webcom.Service", symmetrical=False, blank=True)

    @property
    def total_price(self):
        """
        Total price of service based on services' price and total prce of included services.
        :return: Money
        """
        if self.included.count() > 0:
            prices = map(lambda service: service.total_price, self.included.all())
            return reduce(lambda summary, price: summary + price, prices) + self.price
        return self.price

    def clean(self):
        """
        Validation method of model, raises ValueError if data is not valid.
        :return: None
        """
        if not self.id:
            return
        if self in self.included.all():
            raise ValueError("{} cannot include itself...".format(str(self)))
        if self.included.count() > 3:
            raise ValueError("{} cannot include more than 3 service...".format(str(self)))
        if self.included.annotate(included_count=Count('included'))\
                .filter(included_count__gt=0)\
                .exists():
            raise ValueError("{} cannot include services that has another includes...".format(str(self)))

    def __str__(self):
        """
        To string method
        :return: str
        """
        return "Service: {} {}".format(self.name, self.price)


class Addendum(models.Model):
    """
    Model representing addendum data of contract in the system.
    """
    # Required creation datetime field.
    datetime_created = models.DateTimeField()
    # Set of included services
    services = models.ManyToManyField("webcom.Service")
    # Optional regular contract base
    regular_contract = models.ForeignKey("webcom.RegularContract",
                                         related_name="%(class)ss",
                                         on_delete=models.CASCADE,
                                         blank=True, null=True)
    # Optional business contract base
    business_contract = models.ForeignKey("webcom.BusinessContract",
                                          related_name="%(class)ss",
                                          on_delete=models.CASCADE,
                                          blank=True, null=True)

    def clean(self):
        """
        Validation method of model, raises ValueError if data is not valid.
        :return: None
        """
        if self.regular_contract and self.business_contract:
            raise ValidationError(_("Addendum can belong either to Regular Contract or Business but not both..."))

    @property
    def contract(self):
        """
        Property getter for contract base
        :return: RegularContract|BusinessContract
        """
        if hasattr(self, "regular_contract"):
            return self.regular_contract
        return self.business_contract

    @contract.setter
    def contract(self, contract):
        """
        Property setter for contract base
        :return: RegularContract|BusinessContract
        """
        if not self.regular_contract and not self.business_contract:
            if isinstance(contract, RegularContract):
                self.regular_contract = contract
            else:
                self.business_contract = contract
        else:
            raise ValueError("Addendum already has contract assigned to it: %s" % str(self.contract))

    def __str__(self):
        """
        To string method
        :return: str
        """
        return "Addendum: {} -> {}".format(self.datetime_created, str(self.contract))


class Employee(Person, ContactDataMixin):
    """
    Abstract class representing Employee type instance in the system,
    extends Person and ContactDataMixin class.
    """
    # Required employee's salary field :type: Money
    salary = MoneyField(max_digits=10, decimal_places=2, null=False, blank=False)
    # Required employee's seniority information :type: int
    seniority = models.PositiveSmallIntegerField(blank=False)

    # Meta class for specifing properties of class
    class Meta:
        abstract = True

    def bonus(self):
        """
        Abstract method for calculating salary bonus of employee.
        """
        raise NotImplemented


class TechnicalEmployee(Employee):
    """
    Class for representing technical employee in the system, extends Employee class.
    """
    # TECHNICIAN enum type of technical employee
    TECHNICIAN = "Technician"
    # SYSADMIN enum type of technical employee
    SYSADMIN = "SysAdmin"
    choices = (
        (TECHNICIAN,"Technician"),
        (SYSADMIN, "System administrator")
    )

    # Required field for storing enum type of technical employee
    employee_type = models.CharField(max_length=10, choices=choices, blank=False)

    @classmethod
    def create(cls, type, email, phone_number, **kwargs):
        """
        Classmethid for creating TechnicalEmployee type instances
        :param type: enum type of technical employee
        :param email: str
        :param phone_number: str
        :param kwargs: key value argumnents
        :return: TechnicalEmployee
        """
        t_emp = cls(email=email, phone_number=phone_number, **kwargs)
        t_emp.instance = type
        return t_emp

    @property
    def instance(self):
        """
        Property getter of current type extension of Technical Employee
        :return: Technician|SysAdmin
        """
        if self.employee_type == TechnicalEmployee.TECHNICIAN:
            return self.technician
        else:
            return self.sysadmin

    @instance.setter
    def instance(self, employee_type):
        """
        Property setter of current type extension of Technical Employee
        :return: None
        """
        if employee_type == TechnicalEmployee.TECHNICIAN:
            if self.employee_type == TechnicalEmployee.SYSADMIN:
                self.sysadmin.delete()
                self.technician = Technician()
            elif self.employee_type not in (TechnicalEmployee.TECHNICIAN, TechnicalEmployee.SYSADMIN):
                self.technician = Technician()
            self.employee_type = TechnicalEmployee.TECHNICIAN
        else:
            if self.employee_type == TechnicalEmployee.TECHNICIAN:
                self.technician.delete()
                self.sysadmin = SysAdmin()
            elif self.employee_type not in (TechnicalEmployee.TECHNICIAN, TechnicalEmployee.SYSADMIN):
                self.sysadmin = SysAdmin()
            self.employee_type = TechnicalEmployee.SYSADMIN

    @property
    def bonus(self):
        """
        Overridden method for calculating salary bonus of technical employee,
        delegation to extension,
        """
        if self.employee_type == TechnicalEmployee.TECHNICIAN:
            return getattr(self.technician, "bonus")
        else:
            return getattr(self.sysadmin, "bonus")

    def save(self, *args, **kwargs):
        """
        Overridden save method
        :param args: positional argumetns
        :param kwargs: key value arguments
        :return: None
        """
        super().save(*args, **kwargs)
        if self.employee_type == TechnicalEmployee.TECHNICIAN:
            self.technician = self.technician
            self.technician.save()
        else:
            self.sysadmin = self.sysadmin
            self.sysadmin.save()

    def __getattr__(self, item):
        """
        Method for delegating attribute calls to Technician or SysAdmin extension
        :param item: attribute object
        :return: item called from Technician or SysAdmin extension
        """
        return getattr(self.instance, item)

    def delete(self, *args, **kwargs):
        """
        Overridden method for deleting TechnicalEmloyee object from database.
        :param args: positional arguments
        :param kwargs: key dictionary arguments
        :return: TechnicalEmloyee <deleted>
        """
        self.instance.delete()
        return super().delete(*args, **kwargs)


class Technician(models.Model):
    """
    Model for representing technician data in the system.
    """

    # TechnicalEmployee base.
    technicalemployee_base = models.OneToOneField("webcom.TechnicalEmployee",
                                         on_delete=models.CASCADE,
                                         blank=False)

    @property
    def bonus(self):
        """
        Method for calculating salary bonus of technician.
        :return: Money
        """
        return Money("0.0")


class SysAdmin(models.Model):
    """
    Model for representing sysadmin data in the system.
    """

    # TechnicalEmployee base.
    technicalemployee_base = models.OneToOneField("webcom.TechnicalEmployee",
                                                  on_delete=models.CASCADE,
                                                  blank=False)

    @property
    def bonus(self):
        """
        Method for calculating salary bonus of sysadmin.
        :return: Money
        """
        return self.technicalemployee_base.salary*0.1


class RegularEmployee(Employee):
    """
    Abstract model for representing data of regular type employees in the system.
    """
    # Required work experience field :type: str
    workexperience_description = models.CharField(max_length=300, blank=False)
    # Required softskills description field :type: str
    softskills_description = models.CharField(max_length=200, blank=True)

    # Meta class for specifing properties of class
    class Meta:
        abstract=True


class ClientManager(RegularEmployee):

    def bonus(self):
        """
        Method for calculating salary bonus of client manager.
        :return: Money
        """
        return Money("0.0")


class Accountant(RegularEmployee):

    def bonus(self):
        """
        Method for calculating salary bonus of accountant.
        :return: Money
        """
        return Money("0.0")


class Device(models.Model):
    """
    Abstract model for storing device information in the system.
    """
    # Required model name field
    model = models.CharField(max_length=50, blank=False)
    # Required manufacturer name field
    manufacturer = models.CharField(max_length=50, blank=False)

    # Meta class for specifing properties of class
    class Meta:
        abstract = True


class Laptop(Device):
    """
    Model for data about laptops of ISP in the system.
    """
    # All repairs relate to instance
    repairs = models.ManyToManyField("webcom.Technician", through="webcom.LaptopRepair")


class Server(Device):
    """
    Model for data about servers of ISP in the system.
    """
    # All repairs relate to instance
    repairs =  models.ManyToManyField("webcom.Technician", through="webcom.ServerRepair")


class Router(Device):
    """
    Model for data about routers of ISP in the system.
    """
    # All repairs relate to instance
    repairs = models.ManyToManyField("webcom.Technician", through="webcom.RouterRepair")


class Repair(models.Model):
    """
    Abstract class representing information about repair of device in the system.
    """
    # Required datetime field of device repair
    datetime_repaired = models.DateTimeField()
    # Relation to technician who made repair
    technician = models.ForeignKey("webcom.Technician", on_delete=models.CASCADE)

    # Meta class for specifing properties of class
    class Meta:
        abstract=True


class LaptopRepair(Repair):
    """
    Class representing information about laptop repair in the system.
    """
    # Relation to repaired laptop
    laptop = models.ForeignKey("webcom.Laptop", on_delete=models.CASCADE)


class ServerRepair(Repair):
    """
    Class representing information about server repair in the system.
    """
    # Relation to repaired server
    server = models.ForeignKey("webcom.Server", on_delete=models.CASCADE)


class RouterRepair(Repair):
    """
    Class representing information about router repair in the system.
    """
    # Relation to repaired router
    router = models.ForeignKey("webcom.Router", on_delete=models.CASCADE)
