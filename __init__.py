# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .prescription import *
from .specie import *
from .medication_event import *


def register():
    Pool.register(
        Location,
        Move,
        MedicationEvent,
        Party,
        Prescription,
        PrescriptionLine,
        PrescriptionAnimal,
        PrescriptionAnimalGroup,
        Product,
        ProductTemplate,
        Specie,
        Template,
        TemplateLine,
        module='farm_prescription', type_='model')
