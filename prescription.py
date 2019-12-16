# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import datetime
from itertools import chain
from sql import Table

from trytond.model import ModelView, ModelSQL, Workflow, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import Bool, Date, Equal, Eval, If, Or
from trytond import backend
from trytond.exceptions import UserError, UserWarning
from trytond.i18n import gettext

__all__ = ['Party', 'ProductTemplate', 'Product', 'Move', 'Template',
    'TemplateLine', 'Prescription', 'PrescriptionLine', 'PrescriptionAnimal',
    'PrescriptionAnimalGroup', 'Location', 'CreateInternalShipmentStart',
    'CreateInternalShipment']

_STATES = {
    'readonly': Eval('state') != 'draft',
    }
_STATES_REQUIRED = {
    'required': Eval('state') != 'draft',
    'readonly': Eval('state') != 'draft',
    }
_DEPENDS = ['state']


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    veterinarian = fields.Boolean('Veterinarian')
    collegiate_number = fields.Char('Collegiate Number', states={
            'required': Eval('veterinarian', False),
            'invisible': ~Eval('veterinarian', False),
        }, depends=['veterinarian'])


class ProductTemplate(metaclass=PoolMeta):
    __name__ = 'product.template'

    prescription_required = fields.Boolean('Prescription required')


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    prescription_required = fields.Function(fields.Boolean(
            'Prescription required'),
        'on_change_with_prescription_required',
        searcher='search_prescription_required')
    prescription_template = fields.Many2One('farm.prescription.template',
        'Prescription Template',
        domain=[
            ('product', '=', Eval('id')),
            ],
        states={
            'invisible': ~Eval('prescription_required', False),
            },
        depends=['id', 'prescription_required'])

    @fields.depends('_parent_template.prescription_required' , 'template')
    def on_change_with_prescription_required(self, name=None):
        if self.template:
            return self.template.prescription_required
        return False

    @classmethod
    def search_prescription_required(cls, name, clause):
        return [tuple(('template.%s' % name, )) + tuple(clause[1:])]


class PrescriptionMixin:
    '''
    Mixin class with the shared fields and methods by Prescription and Template
    '''
    specie = fields.Many2One('farm.specie', 'Specie', domain=[
            ('prescription_enabled', '=', True),
            ], required=True, readonly=True, select=True)
    type = fields.Selection([
            ('feed', 'Feed'),
            ('medical', 'Medical'),
            ], 'Type', required=True, readonly=True, select=True)
    product = fields.Many2One('product.product', 'Product', domain=[
            ('prescription_required', '=', True),
            ], required=True,
        help='The product for which this recipe is made. This can be a drug '
        'or a feed to which are added the additives or medications defined in '
        'the lines of this recipe.')
    unit = fields.Function(fields.Many2One('product.uom', 'Unit'),
        'on_change_with_unit')
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'on_change_with_unit_digits')
    quantity = fields.Float('Quantity', digits=(16, Eval('unit_digits', 2)),
        required=True, depends=['unit_digits'])
    drug_quantity = fields.Function(fields.Float('Quantity',
            digits=(16, Eval('unit_digits', 2)), depends=['unit_digits']),
        'get_drug_quantity')
    afection = fields.Char('Afection')
    dosage = fields.Char('Dosage')
    waiting_period = fields.Integer('Waiting Period', states={
            'readonly': Eval('n_lines', 0) > 1,
            }, depends=['n_lines'],
        help='The number of days that must pass since the produced feed is '
        'given to animals and they are slaughtered.')
    expiry_period = fields.Integer('Expiry Period')
    n_lines = fields.Function(fields.Integer('Num. of lines'),
        'on_change_with_n_lines')
    note = fields.Text('Note')

    @staticmethod
    def default_specie():
        pool = Pool()
        Specie = pool.get('farm.specie')
        specie = Transaction().context.get('specie')
        if not specie:
            species = Specie.search([], limit=2)
            if len(species) == 1:
                specie, = species
        return specie

    @staticmethod
    def default_type():
        return Transaction().context.get('type', 'feed')

    @staticmethod
    def default_n_lines():
        return 0

    @fields.depends('product')
    def on_change_with_unit(self, name=None):
        if self.product:
            return self.product.default_uom.id
        return None

    @fields.depends('product')
    def on_change_with_unit_digits(self, name=None):
        if self.product:
            return self.product.default_uom.digits
        return 2

    @fields.depends('lines', 'waiting_period')
    def on_change_with_waiting_period(self):
        if self.lines and len(self.lines) > 1:
            return 28
        return self.waiting_period

    @fields.depends('lines')
    def on_change_with_n_lines(self, name=None):
        return len(self.lines) if self.lines else 0

    def get_drug_quantity(self, name):
        Uom = Pool().get('product.uom')
        quantity = 0
        for line in self.lines:
            quantity += Uom.compute_qty(line.unit, line.quantity, self.unit)
        return quantity

    def get_factor_change_quantity_unit(self, new_quantity, new_uom):
        Uom = Pool().get('product.uom')
        if not new_quantity:
            new_quantity = 0
        if new_uom != self.unit:
            new_quantity = Uom.compute_qty(new_uom, new_quantity,
                self.unit)
        if new_quantity != self.quantity:
            # quantity have chaned
            return new_quantity / self.quantity
        return None


class PrescriptionLineMixin:
    '''
    Mixin class with the shared fields and methods by Prescription Line and
    Template Line
    '''
    product = fields.Many2One('product.product', 'Product', domain=[
            ('prescription_required', '=', True),
            ], required=True)
    product_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Uom Category'),
        'on_change_with_product_uom_category')
    unit = fields.Many2One('product.uom', 'Unit', required=True,
        domain=[
            If(Bool(Eval('product_uom_category')),
                ('category', '=', Eval('product_uom_category')),
                ()),
            ],
        depends=['product_uom_category'])
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'on_change_with_unit_digits')
    quantity = fields.Float('Quantity', digits=(16, Eval('unit_digits', 2)),
        depends=['unit_digits'], required=True)

    @fields.depends('product', 'unit', 'unit_digits')
    def on_change_product(self):
        if self.product:
            category = self.product.default_uom.category
            if not self.unit or self.unit not in category.uoms:
                self.unit = self.product.default_uom
                self.unit_digits = self.product.default_uom.digits

    @fields.depends('product')
    def on_change_with_product_uom_category(self, name=None):
        if self.product:
            return self.product.default_uom_category.id

    @fields.depends('unit')
    def on_change_with_unit_digits(self, name=None):
        if self.unit:
            return self.unit.digits
        return 2


class Template(ModelSQL, ModelView, PrescriptionMixin):
    '''Prescription Template'''
    __name__ = 'farm.prescription.template'
    name = fields.Char('Name', required=True, select=True)
    lines = fields.One2Many('farm.prescription.template.line', 'prescription',
        'Lines',
        states={
            'invisible': Eval('type') == 'medical',
            },
        depends=['type'])

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        cursor = Transaction().connection.cursor()
        table = TableHandler(cls, module_name)
        sql_table = cls.__table__()
        product = Table('product_product')
        template = Table('product_template')

        # Upgrade from 3.4: copy name from product rec_name
        upgrade_name = False
        if not table.column_exist('name'):
            upgrade_name = True

        super(Template, cls).__register__(module_name)

        if upgrade_name:
            # copy product name to prescription name
            query = sql_table.join(product,
                condition=(product.id == sql_table.product)).join(template,
                    condition=(product.template == template.id)).select(
                        product.id, template.name)
            cursor.execute(*query)
            for id_, name in cursor.fetchall():
                cursor.execute(*sql_table.update(
                    columns=[sql_table.name],
                    values=[name],
                    where=sql_table.product == id_))

    @fields.depends('product', 'name')
    def on_change_product(self):
        if self.product and not self.name:
            self.name = self.product.rec_name

    @classmethod
    def write(cls, *args):
        pool = Pool()
        Prescription = pool.get('farm.prescription')
        Product = pool.get('product.product')

        actions = iter(args)
        for templates, values in zip(actions, actions):
            if values.get('product'):
                for template in templates:
                    n_template_products = Product.search_count([
                            ('prescription_template', '=', template.id),
                            ])
                    n_template_prescriptions = Prescription.search_count([
                            ('template', '=', template.id),
                            ])
                    if n_template_products or n_template_prescriptions:
                        raise UserError(gettext('farm.prescription.msg_'
                                'template_related_to_product_or_prescription',
                                template=template.rec_name))
        super(Template, cls).write(*args)


class TemplateLine(ModelSQL, ModelView, PrescriptionLineMixin):
    'Prescription Template Line'
    __name__ = 'farm.prescription.template.line'

    prescription = fields.Many2One('farm.prescription.template',
        'Prescription', required=True, ondelete='CASCADE')


class Prescription(Workflow, ModelSQL, ModelView, PrescriptionMixin):
    'Prescription'
    __name__ = 'farm.prescription'
    _rec_name = 'reference'

    template = fields.Many2One('farm.prescription.template', 'Template',
        domain=[
            ('specie', '=', Eval('specie')),
            ],
        states=_STATES, depends=_DEPENDS + ['specie', 'product'])
    reference = fields.Char('Reference', select=True, states=_STATES_REQUIRED,
        depends=_DEPENDS,
        help='If there is a real prescription; put its reference here. '
        'Otherwise, leave it blank and it will be computed automatically with '
        'the configured sequence.')
    date = fields.Date('Date', required=True, states=_STATES, depends=_DEPENDS)
    farm = fields.Many2One('stock.location', 'Farm', required=True,
        states=_STATES, depends=_DEPENDS, domain=[
            ('type', '=', 'warehouse'),
            ('id', 'in', Eval('context', {}).get('farms', [])),
        ],
        context={
            'restrict_by_specie_animal_type': True,
        })
    delivery_date = fields.Date('Delivery date', required=True, domain=[
            ['OR',
                ('delivery_date', '=', None),
                ('delivery_date', '>=', Eval('date', Date()))],
            ],
        states=_STATES, depends=_DEPENDS+['date'])
    veterinarian = fields.Many2One('party.party', 'Veterinarian', domain=[
            ('veterinarian', '=', True),
            ],
        states=_STATES_REQUIRED, depends=_DEPENDS)
    lot = fields.Many2One('stock.lot', 'Lot', domain=[
            ('product', '=', Eval('product')),
            ],
        states={
            'required': Eval('state') == 'done',
            'readonly': Eval('state') == 'done',
            }, depends=_DEPENDS + ['product'])
    number_of_animals = fields.Integer('Number of animals',
        states={
            'readonly': Eval('state') != 'draft',
            'required': ((Eval('state') != 'draft')
                & ~Bool(Eval('animals'))
                & ~Bool(Eval('animal_groups'))),
            },
        depends=['state', 'animals', 'animal_groups'])
    animals = fields.Many2Many('farm.prescription-animal', 'prescription',
        'animal', 'Animals', domain=[
            ('specie', '=', Eval('specie')),
            If(Equal(Eval('state'), 'draft'),
                ('farm', '=', Eval('farm')),
                ()),
            ],
        states={
            'readonly': Eval('state') != 'draft',
            'required': ((Eval('state') != 'draft')
                & ~Bool(Eval('number_of_animals'))
                & ~Bool(Eval('animal_groups'))),
            },
        depends=['specie', 'farm', 'state', 'number_of_animals',
            'animal_groups'])
    animal_groups = fields.Many2Many('farm.prescription-animal.group',
        'prescription', 'group', 'Animal Groups', domain=[
            ('specie', '=', Eval('specie')),
            If(Equal(Eval('state'), 'draft'),
                ('farms', 'in', [Eval('farm')]),
                ()),
            ],
        states={
            'readonly': Eval('state') != 'draft',
            'required': ((Eval('state') != 'draft')
                & ~Bool(Eval('number_of_animals'))
                & ~Bool(Eval('animals'))),
            },
        depends=['specie', 'farm', 'state', 'number_of_animals',
            'animals'])
    animal_lots = fields.Function(fields.Many2Many('stock.lot', None, None,
        'Animals Lots'), 'get_animal_lots')
    animals_description = fields.Function(fields.Char('Animals Description'),
        'get_animals_description')
    specie_description = fields.Function(fields.Char('Specie Description'),
        'get_specie_description')
    lines = fields.One2Many('farm.prescription.line', 'prescription', 'Lines',
        states={
            'invisible': Eval('type') == 'medical',
            'readonly': Eval('state') != 'draft',
            'required': ((Eval('type') != 'medical')
                & (Eval('state') != 'draft')),
            },
        depends=['type', 'state'])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ], 'State', readonly=True, required=True, select=True)
    origin = fields.Reference('Origin', selection='get_origin',
        states=_STATES, depends=_DEPENDS)

    @classmethod
    def __setup__(cls):
        pool = Pool()
        Lot = pool.get('stock.lot')

        super(Prescription, cls).__setup__()
        for fname in ('product', 'quantity', 'dosage', 'expiry_period'):
            field = getattr(cls, fname)
            field.states = _STATES
            field.depends += _DEPENDS
        cls.afection.states = _STATES_REQUIRED
        cls.afection.depends = _DEPENDS
        cls.waiting_period.states = {
            'required': Eval('state') != 'draft',
            'readonly': Or(Eval('n_lines', 0) > 1, Eval('state') != 'draft'),
            }
        cls.waiting_period.depends = ['n_lines', 'state']
        cls.product.states = {
            'readonly': Bool(Eval('template', False)),
            }
        cls.product.depends = ['template']
        cls.unit.on_change_with.add('template')

        if hasattr(Lot, 'expiration_date'):
            cls.lot.domain.append(
                If(Eval('state') != 'done',
                    ('expired', '=', False),
                    ()))
            # TODO: use next context when issue4879 whas resolved
            # cls.lot.context['stock_move_date'] = max(
            #     Eval('context', {}).get('stock_move_date', Date()),
            #     Eval('delivery_date', Date()))
            cls.lot.context['stock_move_date'] = Eval('delivery_date', Date())
            cls.lot.depends += ['delivery_date']

        cls._transitions |= set((
                ('draft', 'confirmed'),
                ('confirmed', 'done'),
                ))
        cls._buttons.update({
                'set_template': {
                    'invisible': Eval('state') != 'draft',
                    'readonly': ~Bool(Eval('template', False)),
                    'icon': 'tryton-add',
                    },
                'confirm': {
                    'invisible': Eval('state') != 'draft',
                    'icon': 'tryton-forward',
                    },
                'done': {
                    'invisible': Eval('state') != 'confirmed',
                    'icon': 'tryton-forward'
                    },
                 })

    @staticmethod
    def default_date():
        return datetime.date.today()

    @staticmethod
    def default_state():
        return 'draft'

    def get_rec_name(self, name):
        return '%s - %s (%s)' % (self.reference,
            self.product.rec_name, str(self.date))

    @fields.depends('template')
    def on_change_template(self):
        if self.template:
            self.product = self.template.product

    @fields.depends('animals', 'animal_groups')
    def on_change_with_number_of_animals(self):
        animals = len(self.animals or [])
        for group in (self.animal_groups or []):
            animals += group.quantity
        return animals

    @fields.depends('product')
    def on_change_with_template(self):
        return (self.product.prescription_template.id
            if (self.product and self.product.prescription_template)
            else None)

    def get_animal_lots(self, name):
        return [a.lot.id for a in self.animals + self.animal_groups]

    def get_animals_description(self, name):
        animals = [a.rec_name for a in self.animals]
        groups = ['%sx%s' % (g.quantity, g.rec_name)
            for g in self.animal_groups]
        return ','.join(chain(animals, groups))

    def get_specie_description(self, name):
        return self.specie.rec_name

    @classmethod
    def _get_origin(cls):
        'Return list of Model names for origin Reference'
        return []

    @classmethod
    def get_origin(cls):
        pool = Pool()
        Model = pool.get('ir.model')
        models = cls._get_origin()
        models = Model.search([
                ('model', 'in', models),
                ])
        return [('', '')] + [(m.model, m.name) for m in models]

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirm(cls, prescriptions):
        for prescription in prescriptions:
            if not prescription.veterinarian:
                raise UserError(gettext('farm_prescription.'
                        'msg_veterinarian_required_confirmed',
                        prescription=prescription.rec_name))
            if prescription.type != 'medical' and not prescription.lines:
                raise UserError(gettext(
                        'farm_prescription.msg_lines_required_confirmed',
                        prescription=prescription.rec_name))

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def done(cls, prescriptions):
        pool = Pool()
        Lot = pool.get('stock.lot')

        stock_move_date = Transaction().context.get('stock_move_date')
        for prescription in prescriptions:
            if not prescription.lot:
                raise UserError(gettext('farm_prescription.'
                        'msg_lot_required_done',
                        prescription=prescription.rec_name))
            if hasattr(prescription.lot, 'expiration_date'):
                prescription_date = prescription.delivery_date
                if stock_move_date:
                    prescription_date = max(prescription_date, stock_move_date)
                with Transaction().set_context(
                        stock_move_date=prescription_date):
                    if Lot(prescription.lot.id).expired:
                        raise UserError(gettext('msg_lot_expired',
                                lot=prescription.lot.rec_name,
                                prescription=prescription.rec_name,
                                ))

    @classmethod
    @ModelView.button
    def set_template(cls, prescriptions):
        Warning = Pool().get('res.user.warning')

        for prescription in prescriptions:
            if not prescription.template:
                continue

            key = 'task_msg_lines_will_be_replaced.%d' % prescription.id

            if Warning.check(key):
                raise UserWarning(key, gettext('farm_prescription.msg_lines_will_be_replaced',
                        prescription=prescription.rec_name))
            prescription.set_template_vals()
            prescription.save()

    def set_template_vals(self):
        pool = Pool()
        PrescriptionLine = pool.get('farm.prescription.line')

        if not self.template:
            return

        if self.lines:
            PrescriptionLine.delete(self.lines)

        self.afection = self.template.afection
        self.dosage = self.template.dosage
        self.waiting_period = self.template.waiting_period
        self.expiration_period = self.template.expiration_time

        rate = self.get_factor_change_quantity_unit(self.template.quantity,
            self.template.unit)
        lines = []
        for line_template in self.template.lines:
            line = PrescriptionLine()
            line.set_template_line_vals(line_template, rate)
            lines.append(line)
        self.lines = lines
        self.note = self.template.note

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Sequence = pool.get('ir.sequence.strict')
        Specie = pool.get('farm.specie')

        context_specie_id = Transaction().context.get('specie')
        default_sequence_id = (context_specie_id
            and Specie(context_specie_id).prescription_sequence.id)
        for value in vlist:
            if value.get('reference'):
                continue
            sequence_id = default_sequence_id
            if value.get('specie'):
                sequence_id = Specie(value['specie']).prescription_sequence.id
            value['reference'] = Sequence.get_id(sequence_id)
        return super(Prescription, cls).create(vlist)

    @classmethod
    def copy(cls, prescriptions, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()

        default['reference'] = None
        default['lot'] = None
        default['state'] = 'draft'
        return super(Prescription, cls).copy(prescriptions, default=default)


class PrescriptionAnimal(ModelSQL):
    'Prescription Animal Relation'
    __name__ = 'farm.prescription-animal'

    prescription = fields.Many2One('farm.prescription', 'Prescription',
        select=True, required=True, ondelete='CASCADE')
    animal = fields.Many2One('farm.animal', 'Animal', select=True,
        required=True, ondelete='CASCADE')


class PrescriptionAnimalGroup(ModelSQL):
    'Prescription Animal Group Relation'
    __name__ = 'farm.prescription-animal.group'

    prescription = fields.Many2One('farm.prescription', 'Prescription',
        select=True, required=True, ondelete='CASCADE')
    group = fields.Many2One('farm.animal.group', 'Animal Group', select=True,
        required=True, ondelete='CASCADE')


class PrescriptionLine(ModelSQL, ModelView, PrescriptionLineMixin):
    'Prescription Line'
    __name__ = 'farm.prescription.line'

    prescription = fields.Many2One('farm.prescription', 'Prescription',
        required=True, ondelete='CASCADE')

    def compute_quantity(self, factor):
        pool = Pool()
        Uom = pool.get('product.uom')
        return Uom.round(self.quantity * factor, self.unit.rounding)

    def set_template_line_vals(self, template, rate):
        pool = Pool()
        Uom = pool.get('product.uom')
        self.product = template.product
        self.unit = template.unit
        quantity = ((template.quantity / rate) if rate else template.quantity)
        self.quantity = Uom.round(quantity, self.unit.rounding)


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'
    prescription = fields.Many2One('farm.prescription', 'Prescription')

    @classmethod
    def _get_origin(cls):
        models = super(Move, cls)._get_origin()
        models.append('farm.prescription.line')
        return models

    @classmethod
    def validate(cls, moves):
        super(Move, cls).validate(moves)
        for move in moves:
            move.check_prescription_and_origin()

    def check_prescription_and_origin(self):
        """
        If the move is related to a prescription, it is a move of a
        prescription line (and the lines is its origin) or it a move of the
        prescription's product.
        """
        pool = Pool()
        PrescriptionLine = pool.get('farm.prescription.line')
        Uom = pool.get('product.uom')

        if self.origin and isinstance(self.origin, PrescriptionLine):
            if (not self.prescription or
                    self.origin.prescription != self.prescription):
                raise UserError(gettext('farm_prescription.'
                        'msg_from_prescription_line_invalid_prescription',
                        move=self.rec_name,
                        origin=self.origin.rec_name,
                        ))
            if (self.product != self.origin.product or
                    self.quantity != Uom.compute_qty(self.origin.unit,
                        self.origin.quantity, self.uom)):
                raise UserError(gettext('farm_prescription.'
                        'msg_from_prescription_line_invalid_product_quantity',
                        move=self.rec_name,
                        origin=self.origin.rec_name,
                        ))
        elif self.prescription:
            quantity = Uom.compute_qty(self.prescription.unit,
                self.prescription.quantity + self.prescription.drug_quantity,
                self.uom)
            if (self.product != self.prescription.product or
                    self.quantity != quantity):
                raise UserError(gettext('farm_prescription.'
                    'msg_prescription_invalid_product_quantity',
                        move=self.rec_name,
                        prescription=self.prescription.rec_name,
                        ))

    @classmethod
    def assign(cls, moves):
        for move in moves:
            move.check_prescription_required()
        super(Move, cls).assign(moves)

    @classmethod
    def do(cls, moves):
        for move in moves:
            move.check_prescription_required()
        super(Move, cls).do(moves)

    def check_prescription_required(self):
        pool = Pool()
        FeedEvent = pool.get('farm.feed.event')
        ShipmentIn = pool.get('stock.shipment.in')

        if self.to_location.prescription_required and (
                not self.prescription and self.product.prescription_required
                and not isinstance(self.shipment, ShipmentIn)
                and not isinstance(self.origin, FeedEvent)):
            # Purchases don't require prescription because are made to stock
            raise UserError(gettext('farm_prescription.msg_need_prescription',
                    move=self.rec_name))
        if self.prescription:
            if self.prescription.state == 'draft':
                raise UserError(gettext('farm_prescription.'
                        'msg_unconfirmed_prescription',
                        prescription=self.prescription.rec_name,
                        move=self.rec_name))


class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'

    prescription_required = fields.Boolean('Prescription required')

    @staticmethod
    def default_prescription_required():
        return True


class CreateInternalShipmentStart(ModelView):
    'Create Internal Shipment Start'
    __name__ = "farm.prescription.internal.shipment.start"

    farm = fields.Many2One('stock.location', 'Farm',
        states={
            'invisible': True,
        },
        domain=[
            ('type', '=', 'warehouse'),
        ])
    from_location = fields.Many2One('stock.location', 'From Location',
        domain=[
            ('type', '=', 'storage'),
            ('silo', '=', False),
            ], depends=['farm'], required=True)


class CreateInternalShipment(Wizard):
    'Create Integer Shipment'
    __name__ = "farm.prescription.internal.shipment"

    start = StateView('farm.prescription.internal.shipment.start',
        'farm_prescription.create_internal_shipment_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateAction('stock.act_shipment_internal_form')

    def default_start(self, fields):
        pool = Pool()
        Move = pool.get('stock.move')

        prescriptions = Prescription.browse(
            Transaction().context['active_ids'])

        for prescription in prescriptions:
            farm = prescription.farm
            move = Move.search([
                    ('prescription', '=', prescription)])
            if move:
                raise UserError(gettext('farm_prescription.'
                        'msg_prescription_used',
                        prescription=prescription.reference,
                        shipment=(move[0].shipment and move[0].shipment.code
                            or move[0].id)))
        return {
            'from_location': None,
            'farm': farm.id,
            }

    def do_create_(self, action):
        pool = Pool()
        Prescription = Pool().get('farm.prescription')
        Shipment = pool.get('stock.shipment.internal')
        Company = pool.get('company.company')

        prescriptions = Prescription.browse(
            Transaction().context['active_ids'])

        company = Company.search([
                ('id', '=', Transaction().context.get('company'))])
        company = company and company[0]
        shipments_vals = []
        for prescription in prescriptions:
            shipment_vals = {}
            shipment_vals['from_location'] = self.start.from_location.id
            shipment_vals['to_location'] = (
                prescription.farm.storage_location.id)
            shipment_vals['company'] = company.id

            move = {}
            move['product'] = prescription.product.id
            move['company'] = company.id
            move['lot'] = prescription.lot and prescription.lot.id or None
            move['quantity']= prescription.quantity
            move['unit_price'] = prescription.product.list_price
            move['currency'] =company.currency.id
            move['uom'] = prescription.unit.id
            move['from_location'] = shipment_vals['from_location']
            move['to_location'] = shipment_vals['to_location']
            move['prescription'] = prescription.id
            shipment_vals['moves'] = [['create', [move]]]

            shipments_vals.append(shipment_vals)

        shipments = Shipment.create(shipments_vals)

        data = {}
        data['res_id'] = [s.id for s in shipments]
        return action, data
