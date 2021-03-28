# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import prescription
from . import medication_event
from . import specie

def register():
    Pool.register(
        prescription.Template,
        prescription.TemplateLine,
        prescription.Prescription,
        prescription.PrescriptionLine,
        prescription.PrescriptionAnimal,
        prescription.PrescriptionAnimalGroup,
        prescription.CreateInternalShipmentStart,
        prescription.Location,
        prescription.Move,
        medication_event.MedicationEvent,
        prescription.Party,
        prescription.Product,
        prescription.ProductTemplate,
        specie.Specie,
        module='farm_prescription', type_='model')
    Pool.register(
        prescription.CreateInternalShipment,
        module='farm_prescription', type_='wizard')
