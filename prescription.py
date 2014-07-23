# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import datetime

from trytond.model import ModelView, ModelSQL, Workflow, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.pyson import And, Bool, Equal, Eval, If, Not, Or
from trytond.wizard import Wizard, StateAction, StateTransition
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['Party', 'ProductTemplate', 'Product', 'Move',
    'Template', 'TemplateLine',
    'Prescription', 'PrescriptionLine',
    'PrescriptionAnimal', 'PrescriptionAnimalGroup',
    'PrescriptionReport', 'PrintPrescription']
__metaclass__ = PoolMeta

_STATES = {
    'readonly': Eval('state') != 'draft',
    }
_STATES_REQUIRED = {
    'required': Eval('state') != 'draft',
    'readonly': Eval('state') != 'draft',
    }
_DEPENDS = ['state']


class Party():
    __name__ = 'party.party'

    veterinarian = fields.Boolean('Veterinarian')
    collegiate_number = fields.Char('Collegiate Number', states={
            'required': Eval('veterinarian', False),
            })


class ProductTemplate():
    __name__ = 'product.template'

    prescription_required = fields.Boolean('Prescription required')


class Product:
    __name__ = 'product.product'

    prescription_template = fields.Many2One('farm.prescription.template',
        'Prescription Template', domain=[
            ('feed_product', '=', Eval('id')),
            ], depends=['id'])


class PrescriptionMixin:
    '''
    Mixin class with the shared fields and methods by Prescription and Template
    '''
    specie = fields.Many2One('farm.specie', 'Specie', domain=[
            ('prescription_enabled', '=', True),
            ], required=True, readonly=True, select=True)
    feed_product = fields.Many2One('product.product', 'Feed', required=True,
        help='The product of the base feed which should be complemented with '
        'drugs.')
    unit = fields.Function(fields.Many2One('product.uom', 'Unit',
            on_change_with=['feed_product']),
        'on_change_with_unit')
    unit_digits = fields.Function(fields.Integer('Unit Digits',
            on_change_with=['feed_product', 'unit']),
        'on_change_with_unit_digits')
    quantity = fields.Float('Quantity', digits=(16, Eval('unit_digits', 2)),
        required=True, depends=['unit_digits'])
    afection = fields.Char('Afection')
    dosage = fields.Char('Dosage')
    waiting_period = fields.Integer('Waiting Period', on_change_with=['lines'],
        states={
            'readonly': Eval('n_lines', 0) > 1,
            }, depends=['n_lines'],
        help='The number of days that must pass since the produced feed is '
        'given to animals and they are slaughtered.')
    expiry_period = fields.Integer('Expiry Period')
    n_lines = fields.Function(fields.Integer('Num. of lines',
            on_change_with=['lines']),
        'on_change_with_n_lines')
    note = fields.Text('Note')

    @staticmethod
    def default_specie():
        return Transaction().context.get('specie')

    @staticmethod
    def default_n_lines():
        return 0

    def on_change_with_unit(self, name=None):
        if self.feed_product:
            return self.feed_product.default_uom.id
        return None

    def on_change_with_unit_digits(self, name=None):
        if self.feed_product:
            return self.feed_product.default_uom.digits
        return 2

    def on_change_with_waiting_period(self):
        if self.lines and len(self.lines) > 1:
            return 28

    def on_change_with_n_lines(self, name=None):
        return len(self.lines) if self.lines else 0


class PrescriptionLineMixin:
    '''
    Mixin class with the shared fields and methods by Prescription Line and
    Template Line
    '''
    product = fields.Many2One('product.product', 'Product', domain=[
            ('prescription_required', '=', True),
            ], required=True, on_change=['product', 'unit', 'unit_digits'])
    product_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Uom Category',
            on_change_with=['product']),
        'on_change_with_product_uom_category')
    unit = fields.Many2One('product.uom', 'Unit', required=True,
        domain=[
            If(Bool(Eval('product_uom_category')),
                ('category', '=', Eval('product_uom_category')),
                ()),
            ],
        depends=['product_uom_category'])
    unit_digits = fields.Function(fields.Integer('Unit Digits',
            on_change_with=['unit']),
        'on_change_with_unit_digits')
    quantity = fields.Float('Quantity', digits=(16, Eval('unit_digits', 2)),
        depends=['unit_digits'], required=True)

    def on_change_product(self):
        if not self.product:
            return {}
        res = {}
        category = self.product.default_uom.category
        if not self.unit or self.unit not in category.uoms:
            res['unit'] = self.product.default_uom.id
            self.unit = self.product.default_uom
            res['unit.rec_name'] = self.product.default_uom.rec_name
            res['unit_digits'] = self.product.default_uom.digits
        return res

    def on_change_with_product_uom_category(self, name=None):
        if self.product:
            return self.product.default_uom_category.id

    def on_change_with_unit_digits(self, name=None):
        if self.unit:
            return self.unit.digits
        return 2


class Template(ModelSQL, ModelView, PrescriptionMixin):
    '''Prescription Template'''
    __name__ = 'farm.prescription.template'
    _rec_name = 'feed_product.rec_name'

    lines = fields.One2Many('farm.prescription.template.line', 'prescription',
        'Lines')

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        cls._error_messages.update({
                'template_related_to_product_or_prescription': (
                    'You can not change the Feed Product of Prescription '
                    'Template "%s" because there are products or '
                    'rescriptions already related to this template.\n'
                    'Please, create a new template.'),
                })

    @classmethod
    def write(cls, templates, vals):
        if vals.get('feed_product'):
            for template in templates:
                n_template_products = Product.search_count([
                        ('prescription_template', '=', template.id),
                        ])
                n_template_prescriptions = Prescription.search_count([
                        ('template', '=', template.id),
                        ])
            if n_template_products or n_template_prescriptions:
                cls.raise_user_error(
                    'template_related_to_product_or_prescription',
                    (template.rec_name,))
        super(Template, cls).write(templates, vals)


class TemplateLine(ModelSQL, ModelView, PrescriptionLineMixin):
    'Prescription Template Line'
    __name__ = 'farm.prescription.template.line'

    prescription = fields.Many2One('farm.prescription.template',
        'Prescription', required=True, ondelete='CASCADE')


class Prescription(Workflow, ModelSQL, ModelView, PrescriptionMixin):
    'Prescription'
    __name__ = 'farm.prescription'
    _rec_name = 'reference'

    template = fields.Many2One('farm.prescription.template', 'Template', domain=[
            ('specie', '=', Eval('specie')),
            ('feed_product', '=', Eval('feed_product')),
            ],
        on_change_with=['feed_product'], states=_STATES,
        depends=_DEPENDS + ['specie', 'feed_product'])
    reference = fields.Char('Reference', select=True, states=_STATES_REQUIRED,
        depends=_DEPENDS,
        help='If there is a real prescription; put its reference here. '
        'Otherwise, leave it blank and it will be computed automatically with '
        'the configured sequence.')
    date = fields.Date('Date', required=True, states=_STATES, depends=_DEPENDS)
    farm = fields.Many2One('stock.location', 'Farm', required=True,
        states=_STATES, depends=_DEPENDS, domain=[
            ('type', '=', 'warehouse'),
        ],
        context={
            'restrict_by_specie_animal_type': True,
        })
    delivery_date = fields.Date('Delivery date', required=True, states=_STATES,
        depends=_DEPENDS)
    veterinarian = fields.Many2One('party.party', 'Veterinarian', domain=[
            ('veterinarian', '=', True),
            ],
        states=_STATES_REQUIRED, depends=_DEPENDS)
    feed_lot = fields.Many2One('stock.lot', 'Feed Lot', domain=[
            ('product', '=', Eval('feed_product')),
            ],
        states={
            'required': Eval('state') == 'done',
            'readonly': Eval('state') == 'done',
            }, depends=_DEPENDS + ['feed_product'])
    animals = fields.Many2Many('farm.prescription-animal', 'prescription',
        'animal', 'Animals', domain=[
            ('specie', '=', Eval('specie')),
            If(Equal(Eval('state'), 'draft'),
                ('farm', '=', Eval('farm')),
                ()),
            ],
        states={
            'required': And(Eval('state') != 'draft',
                Not(Bool(Eval('animal_groups')))),
            'readonly': Eval('state') != 'draft',
            }, depends=_DEPENDS + ['specie', 'farm', 'animal_groups'])
    animal_groups = fields.Many2Many('farm.prescription-animal.group',
        'prescription', 'group', 'Animal Groups', domain=[
            ('specie', '=', Eval('specie')),
            If(Equal(Eval('state'), 'draft'),
                ('farms', 'in', [Eval('farm')]),
                ()),
            ],
        states={
            'required': And(Eval('state') != 'draft',
                Not(Bool(Eval('animals')))),
            'readonly': Eval('state') != 'draft',
            }, depends=_DEPENDS + ['specie', 'farm', 'animals'])
    animal_lots = fields.Function(fields.Many2Many('stock.lot', None, None,
        'Animals Lots'), 'get_animal_lots')
    lines = fields.One2Many('farm.prescription.line', 'prescription', 'Lines',
        states=_STATES_REQUIRED, depends=_DEPENDS)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ], 'State', readonly=True, required=True, select=True)
    origin = fields.Reference('Origin', selection='get_origin',
        states=_STATES, depends=_DEPENDS)

    @classmethod
    def __setup__(cls):
        super(Prescription, cls).__setup__()
        for fname in ('feed_product', 'quantity', 'dosage', 'expiry_period'):
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

        cls._error_messages.update({
                'lot_required_done': ('Lot is required to set done the '
                    'prescription "%s".'),
                'veterinarian_required_confirmed': ('Veterinarian is requried '
                    'to confirm the prescription "%s".'),
                'lines_required_confirmed': ('The prescription "%s" must have '
                    'at least one line in order to be confirmed.'),
                 })
        cls._transitions |= set((
                ('draft', 'confirmed'),
                ('confirmed', 'done'),
                ))
        cls._buttons.update({
                'set_template': {
                    'invisible': Eval('state') != 'draft',
                    'readonly': ~Bool(Eval('template', False)),
                    },
                'confirm': {
                    'invisible': Eval('state') != 'draft',
                    },
                'done': {
                    'invisible': Eval('state') != 'confirmed',
                    },
                 })

    @staticmethod
    def default_date():
        return datetime.date.today()

    @staticmethod
    def default_state():
        return 'draft'

    def get_rec_name(self, name):
        return u'%s - %s (%s)' % (self.reference,
            self.feed_product.rec_name, str(self.date))

    def on_change_with_template(self):
        return (self.feed_product.prescription_template.id
            if (self.feed_product and self.feed_product.prescription_template)
            else None)

    def get_animal_lots(self, name):
        return [a.lot.id for a in self.animals + self.animal_groups]

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
                cls.raise_user_error('veterinarian_required_confirmed',
                    prescription.rec_name)
            if not prescription.lines:
                cls.raise_user_error('lines_required_confirmed',
                    prescription.rec_name)

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def done(cls, prescriptions):
        for prescription in prescriptions:
            if not prescription.feed_lot:
                cls.raise_user_error('lot_required_done',
                    prescription.rec_name)

    @classmethod
    @ModelView.button
    def set_template(cls, prescriptions):
        for prescription in prescriptions:
            if not prescription.template:
                continue
            # prescription.set_template_vals()
            vals = prescription.template._save_values
            print "vals:", vals
            # prescription.save()

    def set_template_vals(self):
        pool = Pool()
        PrescriptionLine = pool.get('farm.prescription.line')
        lines = []
        for ql in self.template.lines:
            line = PrescriptionLine()
            line.set_template_line_vals(ql)
            lines.append(line)
        self.lines = lines

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Sequence = pool.get('ir.sequence.strict')
        Specie = pool.get('farm.specie')

        context_specie_id = Transaction().context.get('specie')
        default_sequence_id = (context_specie_id
            and Specie(context_specie_id).prescription_sequence.id)
        for value in vlist:
            sequence_id = default_sequence_id
            if value.get('specie'):
                sequence_id = Specie(value['specie']).prescription_sequence.id
            value['reference'] = Sequence.get_id(sequence_id)
        return super(Prescription, cls).create(vlist)

    @classmethod
    def copy(cls, prescriptions, default=None):
        pool = Pool()
        Sequence = pool.get('ir.sequence.strict')

        if default is None:
            default = {}
        default = default.copy()
        default['reference'] = None
        default['feed_lot'] = None
        default['state'] = 'draft'
        new_prescriptions = super(Prescription, cls).copy(prescriptions,
            default=default)
        for prescription in new_prescriptions:
            prescription.reference = Sequence.get_id(
                prescription.specie.prescription_sequence.id)
            prescription.save()
        return new_prescriptions


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
        Uom = Pool().get('product.uom')
        return Uom.round(self.quantity * factor, self.unit.rounding)


class PrescriptionReport(JasperReport):
    'Prescription'
    __name__ = 'farm.prescription.report'


class PrintPrescription(Wizard):
    'Print Prescription Report'
    __name__ = 'farm.prescription.print'
    start = StateTransition()
    print_ = StateAction('farm_prescription.act_report_prescription')

    def transition_start(self):
        return 'print_'

    def do_print_(self, action):
        data = {}
        data['id'] = Transaction().context['active_ids'].pop()
        data['ids'] = [data['id']]
        return action, data


class Move:
    __name__ = 'stock.move'

    prescription = fields.Many2One('farm.prescription', 'Prescription')

    @classmethod
    def __setup__(cls):
        super(Move, cls).__setup__()
        cls._error_messages.update({
                'from_prescription_line_invalid_prescription': (
                    'The Stock Move "%(move)s" has the Prescription Line '
                    '"%(origin)s" as origin, but it isn\'t related to a '
                    'Prescription or it isn\'t the origin\'s prescription.'),
                'from_prescription_line_invalid_product_quantity': (
                    'The Stock Move "%(move)s" has the Prescription Line '
                    '"%(origin)s" as origin, but the product and/or quantity '
                    'are not the same.'),
                'prescription_invalid_product_quantity': (
                    'The Stock Move "%(move)s" is related to Prescription '
                    '"%(prescription)s", but the product and/or quantity are '
                    'not the same.'),
                'need_prescription': ('Move "%s" needs a confirmed '
                    'prescription'),
                'unconfirmed_prescription': ('Prescription "%s" of move "%s" '
                    'must be confirmed before assigning the move'),
                })

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
                self.raise_user_error(
                    'from_prescription_line_invalid_prescription', {
                        'move': self.rec_name,
                        'origin': self.origin.rec_name,
                        })
            if (self.product != self.origin.product or
                    self.quantity != Uom.compute_qty(self.origin.unit,
                        self.origin.quantity, self.uom)):
                self.raise_user_error(
                    'from_prescription_line_invalid_product_quantity', {
                        'move': self.rec_name,
                        'origin': self.origin.rec_name,
                        })
        elif self.prescription:
            if (self.product != self.prescription.feed_product or
                    self.quantity != Uom.compute_qty(self.prescription.unit,
                        self.prescription.quantity, self.uom)):
                self.raise_user_error(
                    'prescription_invalid_product_quantity', {
                        'move': self.rec_name,
                        'prescription': self.prescription.rec_name,
                        })

    @classmethod
    def assign(cls, moves):
        for move in moves:
            move.check_prescription_required()
        super(Move, cls).assign(moves)

    def check_prescription_required(self):
        pool = Pool()
        ShipmentOut = pool.get('stock.shipment.out')
        if (not self.prescription and
                self.product.prescription_required and (
                    self.shipment and isinstance(self.shipment, ShipmentOut)
                    or self.production_input)):
            self.raise_user_error('need_prescription', self.rec_name)
        elif self.prescription:
            if self.prescription.state == 'draft':
                self.raise_user_error('unconfirmed_prescription',
                    (self.prescription.rec_name, self.rec_name))
