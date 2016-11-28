=====================
Scenario Prescription
=====================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create config::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install Prescriptions::

	>>> Module = Model.get('ir.module.module')
    >>> module, = Module.find([('name', '=', 'farm_prescription')])
    >>> Module.install ([module.id], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

	>>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='U.S. Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.', mon_thousands_sep=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create inner location::

	>>> Location = Model.get('stock.location')
	>>> inner_farm = Location()
	>>> inner_farm.name = "Test Farm/Inner Farm"
	>>> inner_farm.code = "TFARMI"
	>>> inner_farm.type = "storage"
	>>> inner_farm.save()

Create production location::

	>>> production_farm = Location()
	>>> production_farm.name = "Test Farm/Production Farm"
	>>> production_farm.code = "TFARMP"
	>>> production_farm.type = "production"
	>>> production_farm.save()

Create lost and found::

	>>> lost_n_found = Location()
	>>> lost_n_found.name = "Test Lost and Found"
	>>> lost_n_found.code = "TLNF"
	>>> lost_n_found.type = "lost_found"
	>>> lost_n_found.save() 

Create farm::

	>>> farm = Location()
	>>> farm.name = "Test Farm"
	>>> farm.code = "TFARM"
	>>> farm.input_location = inner_farm
	>>> farm.output_location = inner_farm
	>>> farm.storage_location = inner_farm
	>>> farm.production_location = production_farm
	>>> farm.save()

Create products::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> individual_template = ProductTemplate(
    ...     name='Male Pig',
    ...     default_uom=unit,
    ...     type='goods',
    ...     list_price=Decimal('40'),
    ...     cost_price=Decimal('25'))
    >>> individual_template.save()
    >>> individual_product = Product(template=individual_template)
    >>> individual_product.save()
    >>> group_template = ProductTemplate(
    ...     name='Group of Pig',
    ...     default_uom=unit,
    ...     type='goods',
    ...     list_price=Decimal('30'),
    ...     cost_price=Decimal('20'))
    >>> group_template.save()
    >>> group_product = Product(template=group_template)
    >>> group_product.save()

Create sequence::

    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> event_order_sequence = Sequence(
    ...     name='Event Order Pig Warehouse 1',
    ...     code='farm.event.order',
    ...     padding=4)
    >>> event_order_sequence.save()
    >>> individual_sequence = Sequence(
    ...     name='Individual Pig Warehouse 1',
    ...     code='farm.animal',
    ...     padding=4)
    >>> individual_sequence.save()
    >>> group_sequence = Sequence(
    ...     name='Groups Pig Warehouse 1',
    ...     code='farm.animal.group',
    ...     padding=4)
    >>> group_sequence.save()
    >>> party_sequence, = Sequence.find([('name', '=', 'Party')])
    >>> prescription_sequence = SequenceStrict()
    >>> prescription_sequence.name = "Prescription Sequence"
    >>> prescription_sequence.code = 'farm.prescription'
    >>> prescription_sequence.save()

Create species::

	>>> Specie = Model.get('farm.specie')
    >>> SpecieBreed = Model.get('farm.specie.breed')
    >>> SpecieFarmLine = Model.get('farm.specie.farm_line')
    >>> warehouse, = Location.find([('type', '=', 'warehouse')])
    >>> pigs_specie = Specie(
    ...     name='Pigs',
    ...     male_enabled=False,
    ...     female_enabled=False,
    ...     individual_enabled=True,
    ...     individual_product=individual_product,
    ...     group_enabled=True,
    ...     group_product=group_product,
    ...		prescription_enabled=True,
    ...		prescription_sequence=prescription_sequence,
    ...     removed_location=lost_n_found,
    ...     foster_location=lost_n_found,
    ...     lost_found_location=lost_n_found,
    ...     feed_lost_found_location=lost_n_found)    
    >>> pigs_specie.save()
    >>> pigs_breed = SpecieBreed(
    ...     specie=pigs_specie,
    ...     name='Holland')
    >>> pigs_breed.save()
    >>> pigs_farm_line = SpecieFarmLine(
    ...     specie=pigs_specie,
    ...     event_order_sequence=event_order_sequence,
    ...     farm=warehouse,
    ...     has_individual=True,
    ...     individual_sequence=individual_sequence,
    ...     has_group=True,
    ...     group_sequence=group_sequence)
    >>> pigs_farm_line.save()

Create medicine product::

	>>> ProductTemplate = Model.get('product.template')
	>>> ProductUOM = Model.get('product.uom')
	>>> product_template = ProductTemplate()
	>>> product_template.name = "Template product test"
	>>> product_template.type = 'goods'
	>>> product_template.prescription_required = True
	>>> product_template.unique_variant = True
	>>> product_template.cost_price = Decimal('00.00')
	>>> product_template.list_price = Decimal('00.00')
	>>> uom, = ProductUOM.find([('name', '=', 'Unit')])
	>>> product_template.default_uom = uom
	>>> product_template.save()

Create prescription template::

	>>> PrescriptionTemplate = Model.get('farm.prescription.template')
	>>> Product = Model.get('product.product')
	>>> product, = Product.find([('name', '=', 'Template product test')])
	>>> product.prescription_required = True
	>>> product.save()
	>>> prescription_template = PrescriptionTemplate()
	>>> prescription_template.product = product
	>>> prescription_template.quantity = Decimal('1.0')
	>>> #prescription_template.specie = pigs_specie
	>>> prescription_template.save()

Create vet::

	>>> vet = Party(name="Veterinary")
	>>> vet.save()

Create prescription::

	>>> Prescription = Model.get('farm.prescription')
	>>> prescription = Prescription()
	>>> prescription.reference = "Test prescription"
	>>> prescription.farm = warehouse
    >>> prescription.quantity = Decimal('01.00')
    >>> prescription.delivery_date = today
	>>> prescription.template = prescription_template
	>>> prescription_template.product = product
	>>> prescription_template.quantity = Decimal('01.00')
	>>> prescription_template.delivery_date = today
	>>> prescription_template.number_of_animals = 1
	>>> prescription_template.save()
    >>> prescription.save()

Create internal shipment::


	>>> create_internal_shipment = Wizard('farm.prescription.internal.shipment', models=[prescription])
    >>> invoice_wizard = create_internal_shipment.form
    >>> invoice_wizard.from_location = inner_farm
	>>> create_internal_shipment.execute('create_')

Check internal shipment::

    >>> ShipmentInternal = Model.get('stock.shipment.internal')
    >>> internal_moves = ShipmentInternal.find([()])
    >>> len(internal_moves)
    1
    >>> internal_moves, = internal_moves
    >>> internal_moves.from_location == inner_farm
    True
    >>> len(internal_moves.moves)
    1
    >>> internal_moves.moves[0].rec_name == '1.0u Template product test'
    True
    >>> internal_moves.moves[0].product == product
    True


