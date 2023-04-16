=====================
Scenario Prescription
=====================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company

Activate module::

    >>> config = activate_modules('farm_prescription')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create inner location::

    >>> Location = Model.get('stock.location')
    >>> inner_farm = Location()
    >>> inner_farm.name = "Test Farm/Inner Farm"
    >>> inner_farm.code = "TFARMI"
    >>> inner_farm.type = "storage"
    >>> inner_farm.save()

Check location has 'requires prescription' checked::

    >>> inner_farm.prescription_required == True
    True

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
    ...        prescription_enabled=True,
    ...        prescription_sequence=prescription_sequence,
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
    >>> prescription_template.quantity = Decimal('01.00')
    >>> #prescription_template.specie = pigs_specie
    >>> prescription_template.save()

Create vet::

    >>> Party = Model.get('party.party')
    >>> vet = Party(name="Veterinary")
    >>> vet.save()

Create account farm user::

    >>> User = Model.get('res.user')
    >>> farm_user = User()
    >>> farm_user.name = 'Farm User'
    >>> farm_user.login = 'farm_user'
    >>> farm_user.farms.append(Location(warehouse.id))
    >>> Group = Model.get('res.group')
    >>> groups = Group.find([
    ...         ('name', 'in', ['Stock Administration', 'Stock',
    ...             'Product Administration', 'Farm / Prescriptions', 'Farm']),
    ...         ])
    >>> farm_user.groups.extend(groups)
    >>> farm_user.save()
    >>> config.user = farm_user.id

Create prescription::

    >>> today = datetime.date.today()
    >>> Prescription = Model.get('farm.prescription')
    >>> prescription = Prescription()
    >>> prescription.reference = "Test prescription"
    >>> prescription.farm = warehouse
    >>> prescription.quantity = Decimal('01.00')
    >>> prescription.delivery_date = today
    >>> prescription.template = prescription_template
    >>> prescription_template.product = product
    >>> prescription_template.quantity = Decimal('01.00')
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
    >>> internal_moves.moves[0].prescription == prescription
    True

Create no prescription locations::

    >>> medicine_storage = Location()
    >>> medicine_storage.name = "Medicine Storage"
    >>> medicine_storage.code = "MS"
    >>> medicine_storage.type = "storage"
    >>> medicine_storage.prescription_required = False
    >>> medicine_storage.parent = inner_farm
    >>> medicine_storage.save()


Create movement with prescription product to no prescription location::

    >>> Move =  Model.get('stock.move')
    >>> no_prescription_move = Move()
    >>> no_prescription_move.from_location = inner_farm
    >>> no_prescription_move.to_location = medicine_storage
    >>> no_prescription_move.quantity = Decimal('01.00')
    >>> no_prescription_move.product = product
    >>> no_prescription_move.save()


Create internal shipment::

    >>> no_prescription_shipment = ShipmentInternal()
    >>> no_prescription_shipment.from_location = inner_farm
    >>> no_prescription_shipment.to_location = medicine_storage
    >>> no_prescription_shipment.moves.append(no_prescription_move)
    >>> no_prescription_shipment.save()
    >>> no_prescription_shipment.click('wait')
    >>> no_prescription_shipment.click('assign_try')
    False
    >>> no_prescription_shipment.state
    'waiting'

 Create movement with no prescription::

    >>> product_no_prescription, = ProductTemplate.duplicate([product_template], {'name': 'No prescription product','prescription_required': False})
    >>> product2, = Product.find([('name', '=', product_no_prescription.name)], limit=1)
    >>> move = Move()
    >>> move.from_location = inner_farm
    >>> move.to_location = medicine_storage
    >>> move.quantity = Decimal('01.00')
    >>> move.product = product2
    >>> move.save()

Create Lot::

    >>> Lot = Model.get('stock.lot')
    >>> lot = Lot()
    >>> lot.number = '1234'
    >>> lot.product = product2
    >>> lot.save()

Create inventory::

    >>> StockInventory = Model.get('stock.inventory')
    >>> stock_inventory = StockInventory()
    >>> stock_inventory.location = inner_farm
    >>> stock_inventory.lost_found = lost_n_found
    >>> line = stock_inventory.lines.new()
    >>> line.product = product2
    >>> line.quantity = Decimal('10.00')
    >>> stock_inventory.save()
    >>> stock_inventory.click('confirm')

Create internal shipment::

    >>> shipment = ShipmentInternal()
    >>> shipment.from_location = inner_farm
    >>> shipment.to_location = medicine_storage
    >>> shipment.moves.append(move)
    >>> shipment.save()
    >>> shipment.click('wait')
    >>> shipment.click('assign_try')
    True
    >>> shipment.click('done')
    >>> shipment.reload()
    >>> shipment.state
    'done'
    >>> shipments = ShipmentInternal.find([])
    >>> len(shipments)
    3
