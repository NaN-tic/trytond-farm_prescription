import datetime
import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.modules.company.tests.tools import create_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules, set_user


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Activate module
        activate_modules('farm_prescription')

        # Create company
        _ = create_company()

        # Create inner location
        Location = Model.get('stock.location')
        warehouse_loc, = Location.find([('code', '=', 'WH')])
        lost_found_loc, = Location.find([('type', '=', 'lost_found')])
        inner_farm = Location()
        inner_farm.name = "Test Farm/Inner Farm"
        inner_farm.code = "TFARMI"
        inner_farm.type = "storage"
        inner_farm.save()

        # Check location has 'requires prescription' checked
        self.assertEqual(inner_farm.prescription_required, True)

        # Create production location
        production_farm = Location()
        production_farm.name = "Test Farm/Production Farm"
        production_farm.code = "TFARMP"
        production_farm.type = "production"
        production_farm.save()

        # Create farm
        farm = Location()
        farm.name = "Test Farm"
        farm.code = "TFARM"
        farm.input_location = inner_farm
        farm.output_location = inner_farm
        farm.storage_location = inner_farm
        farm.storage_location = inner_farm
        farm.lost_found_location = lost_found_loc
        farm.production_location = production_farm
        farm.type = 'warehouse'
        farm.save()

        # Create products
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        individual_template = ProductTemplate(name='Male Pig',
                                              default_uom=unit,
                                              type='goods',
                                              list_price=Decimal('40'),
                                              cost_price=Decimal('25'))
        individual_template.save()
        individual_product = Product(template=individual_template)
        individual_product.save()
        group_template = ProductTemplate(name='Group of Pig',
                                         default_uom=unit,
                                         type='goods',
                                         list_price=Decimal('30'),
                                         cost_price=Decimal('20'))
        group_template.save()
        group_product = Product(template=group_template)
        group_product.save()

        # Create sequence
        Sequence = Model.get('ir.sequence')
        SequenceStrict = Model.get('ir.sequence.strict')
        SequenceType = Model.get('ir.sequence.type')
        order_sequence_type, = SequenceType.find([('name', '=', 'Event Order')])
        event_order_sequence = Sequence(name='Event Order Pig Warehouse 1',
                                        sequence_type=order_sequence_type,
                                        padding=4)
        event_order_sequence.save()
        animal_sequence_type, = SequenceType.find([('name', '=', 'Animal')])
        individual_sequence = Sequence(name='Individual Pig Warehouse 1',
                                       sequence_type=animal_sequence_type,
                                       padding=4)
        individual_sequence.save()
        animal_group_sequence_type, = SequenceType.find([('name', '=',
                                                          'Animal Group')])
        group_sequence = Sequence(name='Groups Pig Warehouse 1',
                                  sequence_type=animal_group_sequence_type,
                                  padding=4)
        group_sequence.save()
        party_sequence, = Sequence.find([('name', '=', 'Party')])
        prescription_sequence_type, = SequenceType.find([('name', '=',
                                                          'Prescription')])
        prescription_sequence = SequenceStrict()
        prescription_sequence.name = "Prescription Sequence"
        prescription_sequence.sequence_type = prescription_sequence_type
        prescription_sequence.save()

        # Create species
        Specie = Model.get('farm.specie')
        SpecieBreed = Model.get('farm.specie.breed')
        SpecieFarmLine = Model.get('farm.specie.farm_line')
        pigs_specie = Specie(name='Pigs',
                             male_enabled=False,
                             female_enabled=False,
                             individual_enabled=True,
                             individual_product=individual_product,
                             group_enabled=True,
                             group_product=group_product,
                             prescription_enabled=True,
                             prescription_sequence=prescription_sequence,
                             removed_location=lost_found_loc,
                             foster_location=lost_found_loc,
                             lost_found_location=lost_found_loc,
                             feed_lost_found_location=lost_found_loc)
        pigs_specie.save()
        pigs_breed = SpecieBreed(specie=pigs_specie, name='Holland')
        pigs_breed.save()
        pigs_farm_line = SpecieFarmLine(
            specie=pigs_specie,
            event_order_sequence=event_order_sequence,
            farm=warehouse_loc,
            has_individual=True,
            individual_sequence=individual_sequence,
            has_group=True,
            group_sequence=group_sequence)
        pigs_farm_line.save()

        # Create medicine product
        ProductTemplate = Model.get('product.template')
        ProductUOM = Model.get('product.uom')
        product_template = ProductTemplate()
        product_template.name = "Template product test"
        product_template.type = 'goods'
        product_template.prescription_required = True
        product_template.cost_price = Decimal('00.00')
        product_template.list_price = Decimal('00.00')
        uom, = ProductUOM.find([('name', '=', 'Unit')])
        product_template.default_uom = uom
        product_template.save()

        # Create prescription template
        PrescriptionTemplate = Model.get('farm.prescription.template')
        Product = Model.get('product.product')
        product, = Product.find([('name', '=', 'Template product test')])
        product.prescription_required = True
        product.save()
        prescription_template = PrescriptionTemplate()
        prescription_template.product = product
        prescription_template.quantity = Decimal('01.00')
        prescription_template.save()

        # Create vet
        Party = Model.get('party.party')
        vet = Party(name="Veterinary")
        vet.save()

        # Create account farm user
        User = Model.get('res.user')
        farm_user = User()
        farm_user.name = 'Farm User'
        farm_user.login = 'farm_user'
        farm_user.farms.append(Location(warehouse_loc.id))
        Group = Model.get('res.group')
        groups = Group.find([
            ('name', 'in', [
                'Stock Administration', 'Stock', 'Product Administration',
                'Farm / Prescriptions', 'Farm'
            ]),
        ])
        farm_user.groups.extend(groups)
        farm_user.save()
        set_user(farm_user)

        # Create prescription
        today = datetime.date.today()
        Prescription = Model.get('farm.prescription')
        prescription = Prescription()
        prescription.reference = "Test prescription"
        prescription.farm = warehouse_loc
        prescription.quantity = Decimal('01.00')
        prescription.delivery_date = today
        prescription.template = prescription_template
        prescription_template.product = product
        prescription_template.quantity = Decimal('01.00')
        prescription_template.save()
        prescription.save()

        # Create internal shipment
        create_internal_shipment = Wizard('farm.prescription.internal.shipment',
                                          models=[prescription])
        invoice_wizard = create_internal_shipment.form
        invoice_wizard.from_location = inner_farm
        create_internal_shipment.execute('create_')

        # Check internal shipment
        ShipmentInternal = Model.get('stock.shipment.internal')
        internal_moves = ShipmentInternal.find([()])
        self.assertEqual(len(internal_moves), 1)
        internal_moves, = internal_moves
        self.assertEqual(internal_moves.from_location, inner_farm)
        self.assertEqual(len(internal_moves.moves), 1)
        self.assertEqual(internal_moves.moves[0].quantity, 1.0)
        self.assertEqual(internal_moves.moves[0].product, product)
        self.assertEqual(internal_moves.moves[0].prescription, prescription)

        # Create no prescription locations
        medicine_storage = Location()
        medicine_storage.name = "Medicine Storage"
        medicine_storage.code = "MS"
        medicine_storage.type = "storage"
        medicine_storage.prescription_required = False
        medicine_storage.parent = inner_farm
        medicine_storage.save()

        # Create movement with prescription product to no prescription location
        Move = Model.get('stock.move')
        no_prescription_move = Move()
        no_prescription_move.from_location = inner_farm
        no_prescription_move.to_location = medicine_storage
        no_prescription_move.quantity = Decimal('01.00')
        no_prescription_move.product = product
        no_prescription_move.save()

        # Create internal shipment
        no_prescription_shipment = ShipmentInternal()
        no_prescription_shipment.from_location = inner_farm
        no_prescription_shipment.to_location = medicine_storage
        no_prescription_shipment.moves.append(no_prescription_move)
        no_prescription_shipment.save()
        no_prescription_shipment.click('wait')
        no_prescription_shipment.click('assign_try')
        self.assertEqual(no_prescription_shipment.state, 'waiting')

        # Create movement with no prescription
        product_no_prescription, = ProductTemplate.duplicate(
            [product_template], {
                'name': 'No prescription product',
                'prescription_required': False
            })
        product2, = Product.find([('name', '=', product_no_prescription.name)],
                                 limit=1)
        move = Move()
        move.from_location = inner_farm
        move.to_location = medicine_storage
        move.quantity = Decimal('01.00')
        move.product = product2
        move.save()

        # Create Lot
        Lot = Model.get('stock.lot')
        lot = Lot()
        lot.number = '1234'
        lot.product = product2
        lot.save()

        # Create inventory
        StockInventory = Model.get('stock.inventory')
        stock_inventory = StockInventory()
        stock_inventory.location = inner_farm
        line = stock_inventory.lines.new()
        line.product = product2
        line.quantity = Decimal('10.00')
        stock_inventory.save()
        stock_inventory.click('confirm')

        # Create internal shipment
        shipment = ShipmentInternal()
        shipment.from_location = inner_farm
        shipment.to_location = medicine_storage
        shipment.moves.append(move)
        shipment.save()
        shipment.click('wait')
        shipment.click('assign_try')
        shipment.click('done')
        shipment.reload()
        self.assertEqual(shipment.state, 'done')
        shipments = ShipmentInternal.find([])
        self.assertEqual(len(shipments), 3)
