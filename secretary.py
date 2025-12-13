#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, re, logging, shutil
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

class Secretary():

    def __init__(self):
        self.DB_USER = os.getenv("DB_USER", "admin")
        self.DB_PASS = os.getenv("DB_PASSWORD", "1234")
        self.DB_NAME = os.getenv("DB_NAME", "mulsterdb")
        self.DB_PORT = os.getenv("DB_PORT", "5432")
        self.DB_HOST = os.getenv("DB_HOST", "database")
        self.OUTPUT_DIR = Path("Secretary/outputs")
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.supercategory_keywords = {
            "Drums": ["batterie", "batteries", "cymbales", "caisses", "percussions"],
            "Guitars": ["guitare", "guitares"],
            "Bass": ["basse", "basses", "contrebasse"],
            "Keyboards": ["piano", "synthétiseur", "orgue", "clavier", "workstation"],
            "DJ": ["dj", "platine", "mixette"],
            "Mics": ["microphones"],
            "Sono": ["sonorisation", "mixage"],
        }
        self.query = text("""
            SELECT i.*, c.id AS category_id, c.name AS category_name
            FROM instrument_generic i
            LEFT JOIN instrument_category c
            ON c.id = i.instrument_category_id
        """)
        
    def prepare_data(self):
        self.engine = create_engine(f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql_query(self.query, conn)
                df["supercategory"] = df["category_name"].apply(self._assign_supercategory)
                df.drop([
                    "instrument_brand_id", "instrument_category_id", "main_picture_id",
                    "links", "is_published", "base_price_per_day", "scrap_source",
                    "created_at", "updated_at", "slug", "seo_title",
                    "seo_description", "seo_keywords", "push_forward", "category_id"
                ], axis=1, inplace=True, errors="ignore")
                for category, group_df in df.groupby("category_name"):
                    safe_category = self._sanitize_filename(category)
                    supercat = self._assign_supercategory(category)
                    supercat_dir = self.OUTPUT_DIR / self._sanitize_filename(supercat)
                    supercat_dir.mkdir(parents=True, exist_ok=True)
                    output_file = supercat_dir / f"output_{safe_category}.tsv"
                    group_df.to_csv(output_file, sep="\t", index=False)
        except Exception as e:
            logging.error("❌ Connection or export failed:", e)
            return 1
        logging.info(f"✅ Exported rows from Mulster database to processing files. \n")
            
    def _assign_supercategory(self, category_name):
        cat_lower = str(category_name).lower()
        for supercat, keywords in self.supercategory_keywords.items():
            for keyword in keywords:
                if keyword in cat_lower:
                    return supercat
        return "Other"

    def _sanitize_filename(self, name):
        if not name:
            return "unknown"
        name = str(name).strip()
        name = re.sub(r"[^\w\-_.]", "_", name)
        return name or "unknown"
        
    def displace_data(self, supercategories: list[str]):
        pwd_base = Path.cwd()
        input_base = Path(f"Secretary/outputs/")
        if not input_base.is_dir():
            logging.info(f"❌ Error: directory '{input_base}' does not exist.")
            return 1
        for supercategory in supercategories:
            logging.info(f"📦 Copying data for supercategory: {supercategory}")
            input_path = os.path.join(input_base, f"{supercategory}")
            dest_dir = pwd_base / supercategory / "inputs"
            dest_dir.mkdir(parents=True, exist_ok=True)
            for file in os.listdir(input_path):
                file_path = os.path.join(input_path, file)
                category = file.removeprefix("output_").removesuffix(".tsv")
                dest_file = dest_dir / f"input_{category}.tsv"
                shutil.copy(file_path, dest_file)
        logging.info(f"✅ Copied files for processing. \n")

    def clean_errors(self, supercategories: list[str]):
        pwd_base = Path.cwd()
        logging.info(f"🗑 Removing all error CSV files for {len(supercategories)} supercategories \n")
        for supercategory in supercategories:
            file_exists = os.path.isfile(os.path.join(pwd_base, f"{supercategory}/errors.csv"))
            if file_exists:
                os.remove(os.path.join(pwd_base, f"{supercategory}/errors.csv"))

    def clean_outputs(self, supercategories: list[str]):
        pwd_base = Path.cwd()
        logging.info(f"🗑 Removing all output CSV files for {len(supercategories)} supercategories")
        for supercategory in supercategories:
            for file in os.listdir(os.path.join(pwd_base, f"{supercategory}/outputs/")):
                try:
                    os.remove(os.path.join(pwd_base, f"{supercategory}/outputs/{file}"))
                except Exception as e:
                    logging.error(f"❌ Error reading {file}: {e}")
                    return 1

    def clean_answers(self, supercategories: list[str]):
        pwd_base = Path.cwd()
        logging.info(f"🗑 Removing all answer files for {len(supercategories)} supercategories \n")
        for supercategory in supercategories:
            for file in os.listdir(os.path.join(pwd_base, f"{supercategory}/answers/")):
                try:
                    os.remove(os.path.join(pwd_base, f"{supercategory}/answers/{file}"))
                except Exception as e:
                    logging.error(f"❌ Error reading {file}: {e}")
                    return 1

    def clean_prices(self, supercategories: list[str]):
        pwd_base = Path.cwd()
        logging.info(f"🗑 Removing all prices from output files for {len(supercategories)} supercategories \n")
        for supercategory in supercategories:
            try:
                output_path = os.path.join(pwd_base, f"{supercategory}/outputs/")
            except Exception as e:
                logging.error(f"❌ Error reading {error_path}: {e}")
                return 1
            for file in os.listdir(output_path):
                try:
                    df = pd.read_csv(os.path.join(output_path, file))
                    out_df = df.assign(price=None)
                    out_df.to_csv(os.path.join(output_path, file))
                    logging.info(f"✅ Erased {len(df)} output prices from {supercategory}")
                except Exception as e:
                    logging.error(f"❌ Error reading {file}: {e}")
                    return 1
        
    def concatenate_outputs(self, supercategories: list[str]):
        pwd_base = Path.cwd()
        all_dataframes = []
        error_dataframes = []
        logging.info(f"🔍 Gathering CSV files from {len(supercategories)} supercategories")
        for supercategory in supercategories:
            try:
                error_path = os.path.join(pwd_base, f"{supercategory}/errors.csv")
                output_path = os.path.join(pwd_base, f"{supercategory}/outputs/")
                file_exists = os.path.isfile(error_path)
                if file_exists:
                    edf = pd.read_csv(error_path)
                    error_dataframes.append(edf)
                    logging.info(f"✅ Loaded {len(edf)} error rows from {supercategory}")
            except Exception as e:
                logging.error(f"❌ Error reading {error_path}: {e}")
                return 1
            for file in os.listdir(output_path):
                try:
                    df = pd.read_csv(os.path.join(output_path, file))
                    all_dataframes.append(df)
                    logging.info(f"✅ Loaded {len(df)} output rows from {supercategory}")
                except Exception as e:
                    logging.error(f"❌ Error reading {file}: {e}")
                    return 1
            if not all_dataframes or not error_dataframes:
                logging.error("❌ No data files were successfully loaded")
                return 1
        try:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            combined_edf = pd.concat(error_dataframes, ignore_index=True)
            autologue_path = pwd_base / "_catalogue" / "autologue.csv"
            errors_path = pwd_base / "_catalogue" / "errors.csv"
            combined_df.to_csv(autologue_path, index=False)
            combined_edf.to_csv(errors_path, index=False)
            logging.info(f"📊 Concatenated {len(all_dataframes)} files with {len(combined_df)} total rows")
            logging.info(f"💾 Saved to: {autologue_path}")
        except Exception as e:
            logging.error(f"❌ Error concatenating outputs: {e}")
            return 1
