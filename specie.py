#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Not

__all__ = ['Specie']
__metaclass__ = PoolMeta

MODULE_NAME = "farm_prescription"


class Specie:
    __name__ = 'farm.specie'

    prescription_enabled = fields.Boolean('Prescriptions Enabled',
        help="This specie uses prescriptions.")
    prescription_sequence = fields.Many2One('ir.sequence.strict',
        'Prescription Reference Sequence', domain=[
            ('code', '=', 'farm.prescription'),
        ], states={
            'readonly': Not(Bool(Eval('prescription_enabled'))),
            'required': Bool(Eval('prescription_enabled')),
        }, help='Sequence used for prescriptions.')

    @staticmethod
    def default_prescription_enabled():
        return True

    def _create_additional_menus(self, specie_menu, specie_submenu_seq,
            current_menus, current_actions, current_wizards):
        pool = Pool()
        Menu = pool.get('ir.ui.menu')
        ModelData = pool.get('ir.model.data')

        if not self.prescription_enabled:
            return

        specie_submenu_seq = super(Specie,
            self)._create_additional_menus(specie_menu, specie_submenu_seq,
            current_menus, current_actions, current_wizards)

        prescriptions_menu = Menu(ModelData.get_id('farm_prescription',
                'menu_farm_prescriptions'))
        prescription_templates_menu = Menu(
            ModelData.get_id('farm_prescription',
                'menu_farm_prescription_templates'))

        new_domain = [
            ('specie', '=', self.id),
            ]
        new_context = {
            'specie': self.id,
            }
        menu = self._duplicate_menu(prescriptions_menu, specie_menu,
            specie_submenu_seq, current_menus, current_actions,
            current_wizards, new_domain=new_domain, new_context=new_context)

        self._duplicate_menu(prescription_templates_menu, menu, 1,
            current_menus, current_actions, current_wizards,
            new_domain=new_domain, new_context=new_context)
        return specie_submenu_seq + 1
