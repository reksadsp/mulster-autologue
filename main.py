#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, json, logging, subprocess, asyncio, uvicorn
from datetime import datetime, timedelta
from secretary import *
from expert import *

logging.basicConfig(level=logging.INFO)
base_path = os.path.dirname(os.path.abspath(__file__))

class Bass (Expert):
    def __init__(self):
        self.session_id = "default"
        self.source_path = os.path.join(base_path, "Bass/src/")
        self.answer_path = os.path.join(base_path, "Bass/answers/")
        self.input_path = os.path.join(base_path, "Bass/inputs/")
        self.output_path = os.path.join(base_path, "Bass/outputs/")
        super().__init__()
        
    def _expert_filter(self, instrument_data: InstrumentData) -> bool:
        if instrument_data.category == "Baffles Basse":
            if float(instrument_data.price) < 250 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Contrebasse":
            if float(instrument_data.price) < 500 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Tête Basse":
            if float(instrument_data.price) < 250 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Combo Basse":
            if float(instrument_data.price) < 250 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Pédales Basse":
            if float(instrument_data.price) < 25 or float(instrument_data.price) > 600:
                return False
        if instrument_data.category == "Basses Electriques":
            if float(instrument_data.price) < 400 or float(instrument_data.price) > 10000:
                return False
        return True

class DJ (Expert):
    def __init__(self):
        self.session_id = "default"
        self.source_path = os.path.join(base_path, "DJ/src/")
        self.answer_path = os.path.join(base_path, "DJ/answers/")
        self.input_path = os.path.join(base_path, "DJ/inputs/")
        self.output_path = os.path.join(base_path, "DJ/outputs/")
        super().__init__()

    def _expert_filter(self, instrument_data: InstrumentData) -> bool:
        if instrument_data.category == "Platine CD / CD player":
            if float(instrument_data.price) < 600 or float(instrument_data.price) > 3000:
                return False
        if instrument_data.category == "Platine vinyl / Vinyl":
            if float(instrument_data.price) < 600 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Mixette":
            if float(instrument_data.price) < 100 or float(instrument_data.price) > 4000:
                return False
        if instrument_data.category == "Effets DJ / DJ FX":
            if float(instrument_data.price) < 100 or float(instrument_data.price) > 800:
                return False
        return True
        
class Drums (Expert):
    def __init__(self):
        self.session_id = "default"
        self.source_path = os.path.join(base_path, "Drums/src/")
        self.answer_path = os.path.join(base_path, "Drums/answers/")
        self.input_path = os.path.join(base_path, "Drums/inputs/")
        self.output_path = os.path.join(base_path, "Drums/outputs/")
        super().__init__()

    def _expert_filter(self, instrument_data: InstrumentData) -> bool:
        if instrument_data.category == "Batteries Électroniques":
            if float(instrument_data.price) < 300 or float(instrument_data.price) > 10000:
                return False
        if instrument_data.category == "Cymbales":
            if float(instrument_data.price) < 59 or float(instrument_data.price) > 1900:
                return False
        if instrument_data.category == "Percussions Classiques":
            if float(instrument_data.price) < 700 or float(instrument_data.price) > 25000:
                return False
        if instrument_data.category == "Percussions Latines":
            if float(instrument_data.price) < 15 or float(instrument_data.price) > 1300:
                return False
        if instrument_data.category == "Accessoires de Batterie":
            if float(instrument_data.price) < 40 or float(instrument_data.price) > 500:
                return False
        if instrument_data.category == "Batteries Acoust.":
            if float(instrument_data.price) < 300 or float(instrument_data.price) > 10000:
                return False
        if instrument_data.category == "Caisses Claires":
            if float(instrument_data.price) < 80 or float(instrument_data.price) > 3000:
                return False
        return True
        
class Guitars (Expert):
    def __init__(self):
        self.session_id = "default"
        self.source_path = os.path.join(base_path, "Guitars/src/")
        self.answer_path = os.path.join(base_path, "Guitars/answers/")
        self.input_path = os.path.join(base_path, "Guitars/inputs/")
        self.output_path = os.path.join(base_path, "Guitars/outputs/")
        super().__init__()

    def _expert_filter(self, instrument_data: InstrumentData) -> bool:
        if instrument_data.category == "Baffles Guitare":
            if float(instrument_data.price) < 250 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Guitares Electriques":
            if float(instrument_data.price) < 400 or float(instrument_data.price) > 10000:
                return False
        if instrument_data.category == "Accessoires Guitare":
            if float(instrument_data.price) < 15 or float(instrument_data.price) > 300:
                return False
        if instrument_data.category == "Pédales Guitare":
            if float(instrument_data.price) < 25 or float(instrument_data.price) > 600:
                return False
        if instrument_data.category == "Guitares Acoustiques":
            if float(instrument_data.price) < 100 or float(instrument_data.price) > 10000:
                return False
        if instrument_data.category == "Tête Guitare":
            if float(instrument_data.price) < 250 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Combo Guitare":
            if float(instrument_data.price) < 250 or float(instrument_data.price) > 5000:
                return False

        return True

class Keyboards (Expert):
    def __init__(self):
        self.session_id = "default"
        self.source_path = os.path.join(base_path, "Keyboards/src/")
        self.answer_path = os.path.join(base_path, "Keyboards/answers/")
        self.input_path = os.path.join(base_path, "Keyboards/inputs/")
        self.output_path = os.path.join(base_path, "Keyboards/outputs/")
        super().__init__()

    def _expert_filter(self, instrument_data: InstrumentData) -> bool:
        if instrument_data.category == "Piano numérique":
            if float(instrument_data.price) < 200 or float(instrument_data.price) > 20000:
                return False
        if instrument_data.category == "Clavier MIDI":
            if float(instrument_data.price) < 50 or float(instrument_data.price) > 1400:
                return False
        if instrument_data.category == "Piano electrique":
            if float(instrument_data.price) < 1500 or float(instrument_data.price) > 15000:
                return False
        if instrument_data.category == "Pédales Clavier":
            if float(instrument_data.price) < 90 or float(instrument_data.price) > 400:
                return False
        if instrument_data.category == "Amplis clavier":
            if float(instrument_data.price) < 300 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Clavier de scene":
            if float(instrument_data.price) < 900 or float(instrument_data.price) > 15000:
                return False
        if instrument_data.category == "Workstation":
            if float(instrument_data.price) < 500 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Synthétiseur":
            if float(instrument_data.price) < 150 or float(instrument_data.price) > 3500:
                return False
        if instrument_data.category == "Orgue":
            if float(instrument_data.price) < 400 or float(instrument_data.price) > 5000:
                return False
        return True

class Mics (Expert):
    def __init__(self):
        self.session_id = "default"
        self.source_path = os.path.join(base_path, "Mics/src/")
        self.answer_path = os.path.join(base_path, "Mics/answers/")
        self.input_path = os.path.join(base_path, "Mics/inputs/")
        self.output_path = os.path.join(base_path, "Mics/outputs/")
        self.input_file = os.path.join(base_path, "Mics/inputs/input_Microphones.tsv")
        self.output_file = os.path.join(base_path, "Mics/outputs/output_Microphones.csv")
        super().__init__()

    def _expert_filter(self, instrument_data: InstrumentData) -> bool:
        if float(instrument_data.price) < 80 or float(instrument_data.price) > 1900:
            return False
        return True

class Other (Expert):
    def __init__(self):
        self.session_id = "default"
        self.source_path = os.path.join(base_path, "Other/src/")
        self.answer_path = os.path.join(base_path, "Other/answers/")
        self.input_path = os.path.join(base_path, "Other/inputs/")
        self.output_path = os.path.join(base_path, "Other/outputs/")
        self.input_file = os.path.join(base_path, "Other/inputs/input_Accessoires.tsv")
        self.output_file = os.path.join(base_path, "Other/outputs/output_Accessoires.csv")
        super().__init__()

    def _expert_filter(self, instrument_data: InstrumentData) -> bool:
        if float(instrument_data.price) < 15 or float(instrument_data.price) > 300:
            return False
        return True

class Sono (Expert):
    def __init__(self):
        self.session_id = "default"
        self.source_path = os.path.join(base_path, "Sono/src/")
        self.answer_path = os.path.join(base_path, "Sono/answers/")
        self.input_path = os.path.join(base_path, "Sono/inputs/")
        self.output_path = os.path.join(base_path, "Sono/outputs/")
        super().__init__()

    def _expert_filter(self, instrument_data: InstrumentData) -> bool:
        if instrument_data.category == "Tables de mixage":
            if float(instrument_data.price) < 100 or float(instrument_data.price) > 10000:
                return False
        if instrument_data.category == "Set de Sonorisation":
            if float(instrument_data.price) < 200 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Enceintes de Sonorisation":
            if float(instrument_data.price) < 200 or float(instrument_data.price) > 5000:
                return False
        return True

if __name__ == "__main__":

    debug_autologue = False

    # Instanciate agents
    secretary = Secretary()
    bass = Bass()
    dj = DJ()
    drums = Drums()
    guitars = Guitars()
    keyboards = Keyboards()
    mics = Mics()
    other = Other()
    sono = Sono()
    
    # Reset autologue
    if debug_autologue == True:
        # Reset outputs
        secretary.clean_answers(["Bass", "DJ", "Drums", "Guitars", "Keyboards", "Mics", "Other", "Sono"])
        secretary.clean_outputs(["Bass", "DJ", "Drums", "Guitars", "Keyboards", "Mics", "Other", "Sono"])
        secretary.clean_errors(["Bass", "DJ", "Drums", "Guitars", "Keyboards", "Mics", "Other", "Sono"])
        # Reset context
        bass._reset_context()
        dj._reset_context()
        drums._reset_context()
        guitars._reset_context()
        keyboards._reset_context()
        mics._reset_context()
        other._reset_context()
        sono._reset_context()
        # Create inputs
        secretary.prepare_data()
        secretary.displace_data(["Bass", "DJ", "Drums", "Guitars", "Keyboards", "Mics", "Other", "Sono"])
    
    # Update autologue
    try:
        if not os.path.isfile(os.path.join(base_path, "_catalogue/info.json")):
            with open(os.path.join(base_path, "_catalogue/info.json"), "w", encoding="utf-8") as f:
                info = {"last_updated": datetime.now().strftime("%d-%m-%y-%Hh%M:%S")}
                json.dump(info, f, indent=4, ensure_ascii=False)
        with open(os.path.join(base_path, "_catalogue/info.json"), "r", encoding="utf-8") as f:
            info = json.load(f)
            if info.get("last_updated"):
                last = datetime.strptime(info["last_updated"], "%d-%m-%y-%Hh%M:%S")
            if datetime.now() - last > timedelta(days=60):
                logging.info("Updating Autologue...")
                secretary.clean_answers(["Bass", "DJ", "Drums", "Guitars", "Keyboards", "Mics", "Other", "Sono"])
                secretary.clean_prices(["Bass", "DJ", "Drums", "Guitars", "Keyboards", "Mics", "Other", "Sono"])
    except Exception as e:
        logging.error(f"Failed to read info file: {e}")
    
    # Process catalogue
    logging.info("Processing 🐟 ... \n")
    bass.process_multiple_files()
    logging.info("Processing 🎛 ... \n")
    dj.process_multiple_files()
    logging.info("Processing 🥁 ... \n")
    drums.process_multiple_files()
    logging.info("Processing 🎸 ... \n")
    guitars.process_multiple_files()
    logging.info("Processing 🎹 ... \n")
    keyboards.process_multiple_files()
    logging.info("Processing 🎤 ... \n")
    mics.process_file()
    logging.info("Processing 🛠 ... \n")
    other.process_file()
    logging.info("Processing 🔊 ... \n")
    sono.process_multiple_files()
    
    # Export outputs
    secretary.concatenate_outputs(["Bass", "DJ", "Drums", "Guitars", "Keyboards", "Mics", "Other", "Sono"])
