#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
import datetime

from trytond.model import ModelView, ModelSQL, Workflow, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.pyson import And, Bool, Equal, Eval, If, Not
from trytond.wizard import Wizard, StateAction, StateTransition
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['Party', 'Template', 'Prescription', 'PrescriptionLine',
    'PrescriptionAnimal', 'PrescriptionAnimalGroup', 'PrescriptionReport',
    'PrintPrescription', 'Move']
__metaclass__ = PoolMeta

_STATES = {
    'readonly': Eval('state') != 'draft',
}
_DEPENDS = ['state']


class Party():
    __name__ = 'party.party'

    veterinarian = fields.Boolean('Veterinarian')
    collegiate_number = fields.Char('Collegiate Number', states={
            'required': Eval('veterinarian', False),
            })


class Template():
    __name__ = 'product.template'

    prescription_required = fields.Boolean('Prescription required')


class Prescription(Workflow, ModelSQL, ModelView):
    'Prescription'
    __name__ = 'farm.prescription'
    _rec_name = 'reference'

    reference = fields.Char('Reference', readonly=True, select=True, states={
            'required': Eval('state') == 'confirmed',
            })
    date = fields.Date('Date', required=True, states=_STATES, depends=_DEPENDS)
    delivery_date = fields.Date('Delivery date', required=True, states=_STATES,
        depends=_DEPENDS)
    specie = fields.Many2One('farm.specie', 'Specie', domain=[
            ('prescription_enabled', '=', True),
            ], required=True, readonly=True, select=True)
    farm = fields.Many2One('stock.location', 'Farm', required=True,
        states=_STATES, depends=_DEPENDS, domain=[
            ('type', '=', 'warehouse'),
        ],
        context={
            'restrict_by_specie_animal_type': True,
        })
    veterinarian = fields.Many2One('party.party', 'Veterinarian', domain=[
            ('veterinarian', '=', True),
            ],
        states={
            'required': Eval('state') == 'confirmed',
            'readonly': Eval('state') != 'draft',
            }, depends=_DEPENDS)
    feed_product = fields.Many2One('product.product', 'Feed', required=True,
        states=_STATES, depends=_DEPENDS,
        help='The product of the base feed which should be complemented with '
        'drugs.')
    feed_lot = fields.Many2One('stock.lot', 'Feed Lot', domain=[
            ('product', '=', Eval('feed_product')),
            ],
        states={
            'required': Eval('state') == 'done',
            'readonly': Eval('state') == 'done',
            }, depends=_DEPENDS + ['feed_product'])
    unit = fields.Function(fields.Many2One('product.uom', 'Unit',
            on_change_with=['feed_product']),
        'on_change_with_unit')
    unit_digits = fields.Function(fields.Integer('Unit Digits',
            on_change_with=['feed_product', 'unit']),
        'on_change_with_unit_digits')
    quantity = fields.Float('Quantity', digits=(16, Eval('unit_digits', 2)),
        required=True, states=_STATES, depends=_DEPENDS + ['unit_digits'])
    animals = fields.Many2Many('farm.prescription-animal', 'prescription',
        'animal', 'Animals', domain=[
            ('specie', '=', Eval('specie')),
            If(Equal(Eval('state'), 'draft'),
                ('farm', '=', Eval('farm')),
                ()),
            ],
        states={
            'required': And(Eval('state') == 'confirmed',
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
            'required': And(Eval('state') == 'confirmed',
                Not(Bool(Eval('animals')))),
            'readonly': Eval('state') != 'draft',
            }, depends=_DEPENDS + ['specie', 'farm', 'animals'])
    animal_lots = fields.Function(fields.Many2Many('stock.lot', None, None,
        'Animals Lots'), 'get_animal_lots')
    afection = fields.Char('Afection', states=_STATES, depends=_DEPENDS)
    waiting_period = fields.Char('Waiting period', states=_STATES,
        depends=_DEPENDS)
    retention_period = fields.Char('Retention period', states=_STATES,
        depends=_DEPENDS)
    dosage = fields.Char('Dosage', states=_STATES, depends=_DEPENDS)
    lines = fields.One2Many('farm.prescription.line', 'prescription', 'Lines',
        states={
            'required': Eval('state') == 'confirmed',
            'readonly': Eval('state') != 'draft',
            }, depends=_DEPENDS)
    note = fields.Text('Note')
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
        cls._error_messages.update({
                'lot_required_done': 'Lot is required to set done the '
                    'prescription "%s".',
                'veterinarian_required_confirmed': 'Veterinarian is requried '
                    'to confirm the prescription "%s".',
                'lines_required_confirmed': 'The prescription "%s" must have '
                    'at least one line in order to be confirmed.',
                 })
        cls._transitions |= set((
                ('draft', 'confirmed'),
                ('confirmed', 'done'),
                ))
        cls._buttons.update({
                'confirm': {
                    'invisible': Eval('state') != 'draft',
                    },
                'done': {
                    'invisible': Eval('state') != 'confirmed',
                    },
                 })

    @staticmethod
    def default_specie():
        return Transaction().context.get('specie')

    @staticmethod
    def default_date():
        return datetime.date.today()

    @staticmethod
    def default_state():
        return 'draft'

    def get_rec_name(self, name):
        return u'%s - %s (%s)' % (self.reference,
            self.feed_product.rec_name, str(self.date))

    def on_change_with_unit(self, name=None):
        if self.feed_product:
            return self.feed_product.default_uom.id
        return None

    def on_change_with_unit_digits(self, name=None):
        if self.feed_product:
            return self.feed_product.default_uom.digits
        return 2

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


class PrescriptionLine(ModelSQL, ModelView):
    'Prescription Line'
    __name__ = 'farm.prescription.line'

    prescription = fields.Many2One('farm.prescription', 'Prescription',
        required=True, ondelete='CASCADE')
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
                'need_prescription': ('Move "%s" needs a confirmed '
                    'prescription'),
                })

    @classmethod
    def do(cls, moves):
        for move in moves:
            if move.product.prescription_required:
                prescription = move.prescription
                if not prescription or prescription.state == 'draft':
                    cls.raise_user_error('need_prescription',
                        move.rec_name)
        super(Move, cls).do(moves)
