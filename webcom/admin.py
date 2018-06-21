from django.contrib import admin

from webcom.models import Account, \
    RegularContract, \
    RegularCustomer, \
    BusinessCustomer, \
    BusinessContract, \
    Customer, Service, Address, Addendum


class AccountTabularInline(admin.TabularInline):

    model = Account


class RegularContractTabularInline(admin.TabularInline):

    model = RegularContract


class BusinessContractTabularInline(admin.TabularInline):

    model = BusinessContract


class RegularCustomerInline(admin.TabularInline):

    model = RegularCustomer


class BusinessCustomerInline(admin.TabularInline):

    model = BusinessCustomer


class CustomerAdmin(admin.ModelAdmin):

    inlines = [AccountTabularInline,
               RegularCustomerInline,
               BusinessCustomerInline,
               RegularContractTabularInline,
               BusinessContractTabularInline]

    class Meta:
        model = Customer


admin.site.register(Customer, CustomerAdmin)

admin.site.register(Account)
admin.site.register(Address)
admin.site.register(RegularContract)
admin.site.register(BusinessContract)
admin.site.register(Service)
admin.site.register(Addendum)