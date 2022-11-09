# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import If, Bool, Eval
from trytond.modules.farm.events.abstract_event import (
    _STATES_WRITE_DRAFT_VALIDATED, _DEPENDS_WRITE_DRAFT_VALIDATED)


class MedicationEvent(metaclass=PoolMeta):
    __name__ = 'farm.medication.event'
    prescription = fields.Many2One('farm.prescription', 'Prescription',
        domain=[
            ('state', '=', 'done'),
            ('specie', '=', Eval('specie', 0)),
            ('farm', '=', Eval('farm', 0)),
            ('product', '=', Eval('feed_product', 0)),
            If(Bool(Eval('feed_lot')),
                ('lot', '=', Eval('feed_lot', 0)),
                ()),
            ], states=_STATES_WRITE_DRAFT_VALIDATED,
        depends=_DEPENDS_WRITE_DRAFT_VALIDATED + ['specie', 'farm',
            'feed_product', 'feed_lot', 'animal_type', 'animal',
            'animal_group'])

    @fields.depends('specie', 'farm', 'feed_lot', 'animal_type', 'animal',
        'animal_group')
    def on_change_feed_lot(self):
        pool = Pool()
        Prescription = pool.get('farm.prescription')

        try:
            super(MedicationEvent, self).on_change_feed_lot()
        except AttributeError:
            pass
        if self.specie and self.farm and self.feed_lot:
            domain = [
                ('specie', '=', self.specie.id),
                ('farm', '=', self.farm.id),
                ('lot', '=', self.feed_lot.id),
                ('state', '=', 'done'),
                ]
            prescriptions = Prescription.search(domain)
            if prescriptions:
                self.prescription = prescriptions[0]

    @fields.depends('feed_lot', 'prescription')
    def on_change_prescription(self):
        if self.prescription and self.prescription.lot and not self.feed_lot:
            self.feed_lot = self.prescription.lot

    def _get_event_move(self):
        move = super(MedicationEvent, self)._get_event_move()
        move.prescription = self.prescription
        return move
