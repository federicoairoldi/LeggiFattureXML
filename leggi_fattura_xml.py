import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import os

# percorsi e file
NEW_BILLS_FOLDER = r"C:\Users\ACER\Documents\Fatture_xml\nuove"
ARCHIVE_BILLS_FOLDER = r"C:\Users\ACER\Documents\Fatture_xml\archivio"
ERROR_BILLS_FOLDER = r"C:\Users\ACER\Documents\Fatture_xml\errore"
BILLS_DATA = r"G:\Il mio Drive\Fatture\fatture.csv"
SUPPLIERS_DATA = r"G:\Il mio Drive\Fatture\fornitori.csv"


def id_gen_creator():
    i = max(pd.read_csv(BILLS_DATA, sep=';', decimal=',', usecols=["id"]).loc[:,'id']) \
        if os.path.exists(BILLS_DATA) else 0
    
    while True:
        i += 1
        yield i

ID_GEN = id_gen_creator()
        
#### FUNZIONI
def parse_bill_xml(filename):
    fattura = ET.parse(filename)
    
    root = fattura.getroot()
    
    contatti_trasmittente = root.find("FatturaElettronicaHeader")\
                                .find("DatiTrasmissione")\
                                .find("ContattiTrasmittente")
    dati_anagrafici = root.find("FatturaElettronicaHeader")\
                          .find("CedentePrestatore")\
                          .find("DatiAnagrafici")
    
    p_iva = dati_anagrafici.find("IdFiscaleIVA").find("IdPaese").text + \
        dati_anagrafici.find("IdFiscaleIVA").find("IdCodice").text
    email = contatti_trasmittente.find("Email").text if contatti_trasmittente is not None and contatti_trasmittente.find("Email") is not None else None
    telefono = contatti_trasmittente.find("Telefono").text if contatti_trasmittente is not None and contatti_trasmittente.find("Telefono") is not None else None
    anagrafica = dati_anagrafici.find("Anagrafica")
    denominazione_tag = anagrafica.find("Denominazione")
    if denominazione_tag is not None:
        denominazione = denominazione_tag.text
    else:
        denominazione = anagrafica.find("Nome").text + ' ' + anagrafica.find("Cognome").text

    body = root.find("FatturaElettronicaBody")
    dati_gen = body.find("DatiGenerali")
    dati_gen_doc = dati_gen.find("DatiGeneraliDocumento")
    
    numero_fattura = dati_gen_doc.find("Numero").text
    data_fattura = pd.to_datetime(dati_gen_doc.find("Data").text).date()
    if dati_gen_doc.find("ImportoTotaleDocumento") is not None:
        importo = float(dati_gen_doc.find("ImportoTotaleDocumento").text)
    else:
        importo = float(body.find("DatiPagamento").find("DettaglioPagamento").find("ImportoPagamento").text)

    dati_pagamento = body.find("DatiPagamento")
    scadenza = pd.NA
    if dati_pagamento is not None:
        dettaglio_pagamento = dati_pagamento.find("DettaglioPagamento")
        if dettaglio_pagamento is not None:
            data_scadenza = dettaglio_pagamento.find("DataScadenzaPagamento")
            if data_scadenza is not None:
                scadenza = data_scadenza.text

    new_supplier = {
        "PIVA": p_iva,
        "nome": denominazione,
        "email": email,
        "telefono": telefono,
    }
    
    new_bill = {
        "id": None,
        "fornitore": denominazione,
        "numero": '\"' + numero_fattura + '\"',
        "data": data_fattura,
        "importo": importo,
        "scadenza": scadenza,
        "pagato": "no",
        "data pagamento": None,
        "modalita pagamento": None,
    }

    return new_bill, new_supplier


def update_csv(new_bills):
    new_bills = list(new_bills)
    
    if not os.path.exists(BILLS_DATA):
        print('Nessuna base dati csv presente, ne verrà creata una nuova.')
        
        data = pd.DataFrame()
    else:
        data = pd.read_csv(BILLS_DATA, sep=';', decimal=',')
        
        # rimozione fattura già presenti
        new_bills = [
            bill 
            for bill in new_bills 
            if not ((data['fornitore'] == bill['fornitore']) & 
                    (data['numero'] == bill['numero']) & 
                     data['data'] == bill['data']).any()
        ]
    
    # creazione id per nuove fatture
    for bill in new_bills:
        bill['id'] = next(ID_GEN)

    data = pd.concat([data, pd.DataFrame(new_bills)], ignore_index=True)
    
    # update csv (se il file non esiste verrà creato)
    data.drop_duplicates(subset=["fornitore", "numero"])\
        .to_csv(BILLS_DATA, sep=';', decimal=',', index=False)


def update_suppliers_csv(new_suppliers):
    new_suppliers = list(new_suppliers)
    
    if not os.path.exists(SUPPLIERS_DATA):
        print('Nessuna base dati csv presente, ne verrà creata una nuova.')        
        data = pd.DataFrame()
    else:
        data = pd.read_csv(SUPPLIERS_DATA, sep=';', decimal=',', dtype={'PIVA': str})
        
        # rimozione fornitori già presenti
        new_suppliers = [
            supplier 
            for supplier in new_suppliers 
            if not (data['PIVA'] == supplier['PIVA']).any()
        ]

    data = pd.concat([data, pd.DataFrame(new_suppliers)], ignore_index=True)
    
    # update csv (se il file non esiste verrà creato)
    data.drop_duplicates(subset=["PIVA"])\
        .to_csv(SUPPLIERS_DATA, sep=';', decimal=',', index=False)


def add_timestamp_to_name(basename):
    filename, file_extension = os.path.splitext(basename)
    new_name = filename + "_" + datetime.now().strftime("%Y%m%d%H%M%S") + file_extension
    return new_name


def load_bills():
    bills_xml = [
      file
      for file in os.listdir(NEW_BILLS_FOLDER)
      if os.path.splitext(file)[1] == ".xml"
    ]

    new_bills = []
    new_suppliers = []
    for bill in bills_xml:
        try:
            new_bill, new_supplier = parse_bill_xml(os.path.join(NEW_BILLS_FOLDER, bill))

            new_bills.append(new_bill)
            new_suppliers.append(new_supplier)

            destination_folder = ARCHIVE_BILLS_FOLDER
        except:
            destination_folder = ERROR_BILLS_FOLDER

        # spostamento xml in archivio o in errore
        os.rename(
            os.path.join(NEW_BILLS_FOLDER, bill),
            os.path.join(destination_folder, add_timestamp_to_name(bill))
        )

    update_csv(new_bills)
    update_suppliers_csv(new_suppliers)


if __name__ == "__main__":
    load_bills()
