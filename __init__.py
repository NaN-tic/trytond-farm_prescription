# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .prescription import *
from .specie import *
from .medication_event import *


def register():
    Pool.register(
        Template,
        TemplateLine,
        Prescription,
        PrescriptionLine,
        PrescriptionAnimal,
        PrescriptionAnimalGroup,
        Specie,
        Party,
        ProductTemplate,
        Product,
        Move,
        MedicationEvent,
        module='farm_prescription', type_='model')
    Pool.register(
        PrescriptionReport,
        MedicalPrescriptionReport,
        module='farm_prescription', type_='report')
    Pool.register(
        PrintPrescription,
        module='farm_prescription', type_='wizard')
