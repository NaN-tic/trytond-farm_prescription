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

    @classmethod
    def _create_additional_menus(cls, specie, specie_menu, specie_submenu_seq,
            current_menus, current_actions):
        pool = Pool()
        ActWindow = pool.get('ir.action.act_window')
        Group = pool.get('res.group')
        ModelData = pool.get('ir.model.data')

        super(Specie, cls)._create_additional_menus(specie, specie_menu,
                specie_submenu_seq, current_menus, current_actions)

        if not specie.prescription_enabled:
            return

        act_window_prescription = ActWindow(ModelData.get_id(MODULE_NAME,
                'act_prescription'))
        act_window_pres_template = ActWindow(ModelData.get_id(MODULE_NAME,
                'act_template'))
        prescription_group = Group(ModelData.get_id(MODULE_NAME,
                'group_prescription'))

        prescription_menu = cls._create_menu_w_action(specie, [
                ('specie', '=', specie.id),
                ], {
                    'specie': specie.id,
                },
            'Prescriptions', specie_menu, specie_submenu_seq, 'tryton-list',
            prescription_group, act_window_prescription, False, current_menus,
            current_actions)
        specie_submenu_seq += 1

        cls._create_menu_w_action(specie, [
                ('specie', '=', specie.id),
                ], {
                    'specie': specie.id,
                },
            'Prescription Templates', prescription_menu, 1, 'tryton-list',
            prescription_group, act_window_pres_template, False, current_menus,
            current_actions)
