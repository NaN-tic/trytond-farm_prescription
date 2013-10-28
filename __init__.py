#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.

from trytond.pool import Pool
from .prescription import *
from .specie import *


def register():
    Pool.register(
        Specie,
        Party,
        Template,
        Prescription,
        PrescriptionLine,
        PrescriptionAnimal,
        PrescriptionAnimalGroup,
        Move,
        module='farm_prescription', type_='model')
    Pool.register(
        PrescriptionReport,
        module='farm_prescription', type_='report')
    Pool.register(
        PrintPrescription,
        module='farm_prescription', type_='wizard')
