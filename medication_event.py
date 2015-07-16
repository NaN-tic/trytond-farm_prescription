# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import If, Eval

from trytond.modules.farm.events.abstract_event import (
    _STATES_WRITE_DRAFT_VALIDATED, _DEPENDS_WRITE_DRAFT_VALIDATED)

__all__ = ['MedicationEvent']
__metaclass__ = PoolMeta


class MedicationEvent:
    __name__ = 'farm.medication.event'
    prescription = fields.Many2One('farm.prescription', 'Prescription',
        select=True, domain=[
            ('state', '=', 'done'),
            ('specie', '=', Eval('specie', 0)),
            ('farm', '=', Eval('farm', 0)),
            ('product', '=', Eval('feed_product', 0)),
            ('lot', '=', Eval('feed_lot', 0)),
            If(Eval('animal_type') != 'group',
                ('animals', 'in', [Eval('animal', 0)]),
                ('animal_groups', 'in', [Eval('animal_group', 0)])),
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
            res = super(MedicationEvent, self).on_change_feed_lot()
        except AttributeError:
            res = {}
        if self.specie and self.farm and self.feed_lot:
            domain = [
                ('specie', '=', self.specie.id),
                ('farm', '=', self.farm.id),
                ('lot', '=', self.feed_lot.id),
                ('state', '=', 'done'),
                ]
            if self.animal_type != 'group':
                domain.append(('animals', 'in', [self.animal.id]))
            else:
                domain.append(('animal_groups', 'in', [self.animal_group.id]))
            prescriptions = Prescription.search(domain)
            if prescriptions:
                res['prescription'] = prescriptions[0].id
        return res

    def _get_event_move(self):
        move = super(MedicationEvent, self)._get_event_move()
        move.prescription = self.prescription
        return move
