#!/usr/bin/python
# -*- coding: utf-8 -*-
try:
    import requests
except ImportError:
    print("Warning: requests module not available. Install with: pip install requests")
    requests = None

import os, re, json, csv, logging, math, time, subprocess, perplexity, ollama
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from urllib.parse import urlparse
from perplexity import Perplexity
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
import pandas as pd

from knowledge import *
from tool_call import *

base_path = os.path.dirname(os.path.abspath(__file__))

@dataclass
class InstrumentData:

    id: str
    name: str
    type: str
    model: str
    description: str
    price: str
    dimensions: List[str]
    technical_specs: str
    technical_doc: str
    category: str
    confidence_score: float
    llm2llm_score: float
    retries_number: int
    
    def to_csv_dict(self) -> Dict:
        return {
            'id': self.id or 'N/A',
            'name': self.name or 'N/A',
            'type': self.type or 'N/A',
            'model': self.model or 'N/A',
            'description': self.description or 'N/A',
            'price': self.price or 'N/A',
            'length_cm': self.dimensions[0],
            'height_cm': self.dimensions[1],
            'width_cm': self.dimensions[2],
            'weight_kg': self.dimensions[3],
            'technical_specs': self.technical_specs or 'N/A',
            'technical_doc': self.technical_doc or 'N/A',
            'confidence_score': self.confidence_score or '0.0',
            'llm2llm_score': self.llm2llm_score or '0.0',
            'retries_number': self.retries_number or '0'
        }

class Expert():

    def __init__(self):
        load_dotenv()
        self.tools = tools
        self.dimensions_prompt = []
        try:
            self.P_client = Perplexity()
            logging.info("✅ Perplexity Client Enbled \n")
        except Exception as e:
            logging.error("❌ Perplexity Client Error: {e} \n")
        try:
            self.O_client = ollama.Client(host='http://ollama:11434')
            logging.info("✅ Ollama Client Enbled \n")
        except Exception as e:
            logging.error("❌ Ollama Client Error: {e} \n")
        try:
            self.M_client = MCPClient('https://fattily-synetic-arnold.ngrok-free.dev')
            logging.info("✅ MCP Client Enbled \n")
        except Exception as e:
            logging.error("❌ MCP Client Error: {e} \n")
        self.errors_file = os.path.join(self.output_path, "../errors.csv")
        self.context = self._load_context(os.path.join(self.source_path, "context.json"))
        self.price_prompt = self._fetch_prompt(os.path.join(base_path,"prompt-price.md"))
        self.agent_prompt = self._fetch_prompt(os.path.join(self.source_path,"prompt-agent.md"))
        self.technical_prompt = self._fetch_prompt(os.path.join(base_path,"prompt-technical.md"))
        self.dimensions_prompt.append(self._fetch_prompt(os.path.join(base_path,"prompt-longueur.md")))
        self.dimensions_prompt.append(self._fetch_prompt(os.path.join(base_path,"prompt-hauteur.md")))
        self.dimensions_prompt.append(self._fetch_prompt(os.path.join(base_path,"prompt-largeur.md")))
        self.dimensions_prompt.append(self._fetch_prompt(os.path.join(base_path,"prompt-poids.md")))
        self.description_prompt = self._fetch_prompt(os.path.join(base_path,"prompt-description.md"))
        self.documentation_prompt = self._fetch_prompt(os.path.join(base_path,"prompt-documentation.md"))
        self.fieldnames = ['id', 'name', 'type', 'model', 'description', 'price', 'length_cm', 'height_cm', 'width_cm', 'weight_kg', 'technical_specs', 'technical_doc', 'confidence_score', 'llm2llm_score', 'retries_number']

    def process_multiple_files(self):
        for file in os.listdir(self.input_path):
            self.input_file = os.path.join(self.input_path, file)
            filename_without_ext = os.path.splitext(file)[0]
            self.category = filename_without_ext.removeprefix("input_")
            self.output_file = os.path.join(self.output_path, f"output_{self.category}.csv")
            logging.info(f"✅ Researching informations for: {self.category} \n")
            self.process_file()

    def process_file(self):
        full_df = pd.read_table(self.input_file)
        full_df = full_df.map(lambda x: str(x).strip() if pd.notnull(x) else x)
        in_df = full_df.copy()
        in_df.drop(["id", "model", "description", "price", "length_cm", "height_cm", "width_cm", "weight_kg", "technical_specs", "technical_doc", "supercategory"], axis=1, inplace=True, errors="ignore")
        for index, row in in_df.iterrows():
            instrument_data = object.__new__(InstrumentData)
            instrument_data.confidence_score = 0
            instrument_data.llm2llm_score = 0
            instrument_data.retries_number = 0
            instrument_data.id = str(full_df.iloc[index, 0])
            instrument_data.name = str(full_df.iloc[index, 1])
            instrument_data.type = str(full_df.iloc[index, 2])
            instrument_data.model = str(full_df.iloc[index, 3])
            instrument_data.description = str(full_df.iloc[index, 4])
            instrument_data.price = str(full_df.iloc[index, 5])
            instrument_data.dimensions = [str(full_df.iloc[index, 6]), str(full_df.iloc[index, 7]), str(full_df.iloc[index, 8]), str(full_df.iloc[index, 9])]
            instrument_data.technical_specs = str(full_df.iloc[index, 10])
            instrument_data.technical_doc = str(full_df.iloc[index, 11])
            instrument_data.category = str(full_df.iloc[index, 12])
            if self._process_instrument(instrument_data) == "Error":
                logging.error(f"❌ Research failed. \n")
                break
        logging.info(f"✅ Researched {len(in_df)} rows → {self.output_file} \n")

    def _process_instrument(self, instrument_data: InstrumentData):
        if instrument_data.name in self.context["instruments_processed"]:
            return "Processed"
        else:
            if instrument_data.description in (None, 'nan'):
                logging.info(f"🔄 Searching a description for {instrument_data.name}.")
                instrument_data.description = self._chat_perplexity(self.description_prompt, instrument_data.name)
            if instrument_data.price in (None, 'nan'):
                logging.info(f"🔄 Searching a price for {instrument_data.name}.")
                instrument_data.price = self._chat_perplexity(self.price_prompt, instrument_data.name)
            if instrument_data.dimensions in (None, ['nan', 'nan', 'nan', 'nan']) or "0" in instrument_data.dimensions:
                logging.info(f"🔄 Searching dimensions for {instrument_data.name}.")
                for i in range(4):
                    instrument_data.dimensions[i] = self._chat_perplexity(self.dimensions_prompt[i], instrument_data.name)
            if instrument_data.technical_specs in (None, '[]', 'nan', {}):
                logging.info(f"🔄 Searching specifications for {instrument_data.name}.")
                instrument_data.technical_specs = self._chat_perplexity(self.technical_prompt, instrument_data.name)
            if instrument_data.technical_doc in (None, 'nan'):
                logging.info(f"🔄 Searching a documentation for {instrument_data.name}.")
                instrument_data.technical_doc = self._chat_perplexity(self.documentation_prompt, instrument_data.name)
            # Test search results
            if "Error" in (instrument_data.description, instrument_data.price, instrument_data.dimensions[0], instrument_data.dimensions[1], instrument_data.dimensions[2], instrument_data.dimensions[3], instrument_data.technical_specs, instrument_data.technical_doc):
                return "Error"
            if self._validate_instrument_data(instrument_data):
                self._update_context(instrument_data, True)
                instrument_data.confidence_score = self._verif_confidence(instrument_data)
                instrument_data.llm2llm_score = 0.0 #self._verif_llm2llm(instrument_data)
                logging.info(f"✅ {instrument_data.name} processed. \n")
                self._write_instrument(instrument_data, self.output_file)
            else:
                self._update_context(instrument_data, False)
                instrument_data.retries_number = self._check_retries(instrument_data)
                if instrument_data.retries_number > 4:
                    instrument_data.confidence_score = 0.0
                    instrument_data.llm2llm_score = 0.0
                    logging.error(f"❌ Research for {instrument_data.name} incomplete, exitting. \n")
                    self._write_instrument(instrument_data, self.output_file)
                else:
                    instrument_data.confidence_score = 0.0
                    instrument_data.llm2llm_score = 0.0
                    logging.warning(f"❎ Research for {instrument_data.name} failed, retrying... \n")
                    self._write_instrument(instrument_data, self.errors_file)
                    # Relaunch search
                    self._process_instrument(instrument_data)

    def _validate_instrument_data(self, instrument_data: InstrumentData) -> bool:
        instrument_data.description = self._extract_first_paragraph(instrument_data.description)
        instrument_data.price = self._extract_last_number(instrument_data.price)
        instrument_data.dimensions[0] = self._extract_last_number(instrument_data.dimensions[0])
        instrument_data.dimensions[1] = self._extract_last_number(instrument_data.dimensions[1])
        instrument_data.dimensions[2] = self._extract_last_number(instrument_data.dimensions[2])
        instrument_data.dimensions[3] = self._extract_last_number(instrument_data.dimensions[3])
        instrument_data.technical_specs = self._extract_last_json(instrument_data.technical_specs)
        instrument_data.technical_doc = self._extract_last_url(instrument_data.technical_doc)
        if instrument_data.description is None:
            return False
        if instrument_data.price is None:
            return False
        if instrument_data.dimensions is None:
            return False
        if "0" in instrument_data.dimensions:
            return False
        if instrument_data.technical_specs is None:
            return False
        if instrument_data.technical_specs == {}:
            return False
        if instrument_data.technical_doc is None:
            return False
        if not self._expert_filter(instrument_data):
            return False
        return True

    def _verif_confidence(self, instrument_data: InstrumentData) -> float:
        compute_score = 100.0
        cached_prices = []
        cached_dimensions = []
        # Price cache fetching
        for entry in self.context["price_cache"]:
            try:
                price_str = entry.split(" : ")[1]
                cached_prices.append(float(price_str))
            except (ValueError, IndexError):
                continue
        # Dimensions cache fetching
        for entry in self.context["dimensions_cache"]:
            try:
                dims_part = entry.split(" : ")
                dims = eval(dims_part[1])
                if len(dims) == 4:
                    cached_dimensions.append([float(dims[0]), float(dims[1]), float(dims[2]), float(dims[3])])
            except (ValueError, IndexError, SyntaxError):
                continue
        # Price analysis - 50%
        if cached_prices and instrument_data.price is not None:
            if len(cached_prices) != 0:
                avg_price = sum(cached_prices) / len(cached_prices)
                price_diff_percent = abs(float(instrument_data.price) - avg_price) / avg_price * 100
            else:
                price_diff_percent = 0
            if 200 < price_diff_percent <= 300:
                excess_percent = price_diff_percent - 200
                price_penalty = excess_percent * 0.5
                compute_score -= price_penalty
            elif price_diff_percent > 300:
                compute_score -= 50
        # Dimensions analysis - 50%
        if instrument_data.dimensions is not None and len(instrument_data.dimensions) == 4:
            if "0" in instrument_data.dimensions:
                compute_score -= 50
            else:
                if cached_dimensions:
                    avg_dim = 0
                    for i in range(4):
                        clean_dim = re.sub(r'[<>:"/\\|?*]', '', instrument_data.dimensions[i])
                        new_dim = float(clean_dim)
                        for j in range(len(cached_dimensions)):
                            avg_dim += cached_dimensions[j][i]
                        if avg_dim != 0:
                            avg_dim = avg_dim / len(cached_dimensions)
                            dim_diff_percent = abs(new_dim - avg_dim) / avg_dim * 100
                        else:
                            dim_diff_percent = 0
                        if 20 < dim_diff_percent <= 120:
                            excess_percent = dim_diff_percent - 20
                            dimension_penalty = excess_percent * 0.25 * 0.5
                            compute_score -= dimension_penalty
                        elif dim_diff_percent > 120:
                            compute_score -= 12.5
        confidence_score = max(0.0, compute_score)
        confidence_score = min(confidence_score, 100)
        confidence_score = round(confidence_score, 2)
        return confidence_score

    def _verif_llm2llm(self, instrument_data: InstrumentData) -> float:
        compute_score = 100.0
        # Description analysis
        try:
            prompt = f"""Donne une note sur 33 à cette description de produit: {instrument_data.description}"""
            response = self._chat_llama_with_retry(prompt, 3)
            desc_note = float(self._extract_last_number(response))
            logging.info(f"Description score: {desc_note}")
        except Exception as e:
            logging.error(f"Error analyzing description: {e}")
            desc_note = 33
        # Technical analysis
        try:
            prompt = f"""Donne une note sur 33 à cette spécification technique de produit: {instrument_data.technical_specs}"""
            response = self._chat_llama_with_retry(prompt, 3)
            tech_note = float(self._extract_last_number(response))
            logging.info(f"Specs score: {tech_note}")
        except Exception as e:
            logging.error(f"Error analyzing specifications: {e}")
            tech_note = 33
        # Documentation analysis
        try:
            response = requests.get(instrument_data.technical_doc)
            html = response.text
            prompt = f"""Donne une note sur 33 à cette documentation de produit: {html}"""
            response = self._chat_llama_with_retry(prompt, 3)
            doc_note = float(self._extract_last_number(response))
            logging.info(f"Doc score: {doc_note}")
        except Exception as e:
            logging.error(f"Error analyzing documentation: {e}")
            doc_note = 33
        compute_score -= (desc_note + tech_note + doc_note)
        llm2llm_score = max(0.0, compute_score)
        llm2llm_score = min(llm2llm_score, 100)
        llm2llm_score = round(confidence_score, 2)
        return llm2llm_score
        
    def _chat_perplexity(self, prompt, instrument) -> str:
        system_parts = [
            self.agent_prompt,
            f"\n## Utilise les outils de mémorisation de la section 'tools' grâce à cet URL : https://fattily-synetic-arnold.ngrok-free.dev pour enregistrer de manière persistantes tes connaissances et ainsi améliorer ton expertise.",
        ]
        if prompt:
            system_parts.append(f"\n## Tâche de recherche : \n{prompt}")
        messages = [
            {"role": "system", "content": "\n".join(system_parts)},
            {"role": "user", "content": str(instrument)}
        ]
        try:
            result = self.P_client.chat.completions.create(
                messages=messages,
                max_tokens=300,
                model="sonar-pro",
                tools=self.tools
            )
            while result.choices[0].message.tool_calls:
                tool_call = result.choices[0].message.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                result = execute_tool(tool_name, tool_args)
                messages.append({"role": "assistant", "content": result.choices[0].message.content})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
                result = client.chat.completions.create(
                    model="sonar-pro",
                    messages=messages,
                    tools=tools
                )
            if result.choices and len(result.choices) > 0:
                full_response = result.choices[0].message.content
                if full_response:
                    os.makedirs(self.answer_path, exist_ok=True)
                    timestamp = datetime.now().strftime("%d-%m-%y-%Hh%M:%S")
                    filename = re.sub(r'[<>:"/\\|?*]', '', instrument)
                    filename = filename.replace(' ', '_')
                    filename = filename.strip('. ')
                    answer_file = os.path.join(self.answer_path, f"{filename}-answer-{timestamp}.md")
                    with open(answer_file, "w", encoding="utf-8") as f:
                        f.write(full_response)
                    return full_response
            return None
        except perplexity.BadRequestError as e:
            logging.error(f"Invalid search parameters: {e}")
            return None
        except perplexity.APIStatusError as e:
            # logging.error(f"API error: {e.status_code}")
            return "Error"
        except perplexity.RateLimitError:
            if attempt < max_retries - 1:
                delay = (2 ** attempt) + random.uniform(0, 1)
                logging.warning(f"Rate limited, retrying in {delay:.2f}s...")
                time.sleep(delay)
            else:
                logging.error("Max retries reached due to rate limiting")
                return None

    def _chat_llama_with_retry(self, prompt, max_retries=3):
        for attempt in range(max_retries):
            try:
                message = [{"role": "user", "content": prompt}]
                chat = self.O_client.chat(model='phi', messages=message)
                return chat['message']['content']
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                    time.sleep(2)
                else:
                    print(f"❌ Failed after {max_retries} attempts: {e}")
                    raise

    def _reset_context(self):
        self.context = {
            "instruments_processed": [],
            "price_cache": [],
            "dimensions_cache": [],
            "failed_searches": [],
            "last_updated": datetime.now().strftime("%d-%m-%y-%Hh%M:%S"),
            }
        self._save_context(os.path.join(self.source_path, "context.json"))

    def _update_context(self, instrument_data: InstrumentData, state: bool):
        if state:
            self.context["instruments_processed"].append(instrument_data.name)
            self.context["price_cache"].append(f"{instrument_data.name} : {instrument_data.price}")
            self.context["dimensions_cache"].append(f"{instrument_data.name} : {instrument_data.dimensions}")
            if instrument_data.name in self.context["failed_searches"]:
                self.context["failed_searches"].remove(instrument_data.name)
        else:
            if instrument_data.name not in self.context["failed_searches"]:
                self.context["failed_searches"].append(instrument_data.name)
        self._save_context(os.path.join(self.source_path, "context.json"))
        
    def _save_context(self, context_file=None):
        try:
            if os.path.isfile(context_file):
                os.remove(context_file)
            with open(context_file, "w", encoding="utf-8") as f:
                json.dump(self.context, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to write context file: {e}")
            return False
            
    def _load_context(self, context_file=None):
        try:
            if context_file and os.path.isfile(context_file):
                with open(context_file, "r", encoding="utf-8") as f:
                    self.context = json.load(f)
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to load context file: {e}")
            return False

    def _write_instrument(self, instrument_data: InstrumentData, output_file: str):
        try:
            file_exists = os.path.isfile(output_file)
            with open(output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(instrument_data.to_csv_dict())
            return True
        except Exception as e:
            logging.error(f"Failed to write to output CSV: {e}")
            return False

        
    def _check_retries(self, instrument_data: InstrumentData) -> int:
        file_exists = os.path.isfile(self.errors_file)
        if file_exists:
            error_df = pd.read_csv(self.errors_file, encoding='utf-8')
            error_df.drop(["id", "model"], axis=1, inplace=True, errors="ignore")
            mask = error_df['name'].astype(str).str.contains(instrument_data.name, case=False, na=False)
            matching_rows = error_df[mask]
            error_results = {
                'count': len(matching_rows),
                'matches': matching_rows
            }
        else:
            error_df = pd.DataFrame()
            error_results = {
                'count': 0,
                'matches': None
            }
        if error_results['count'] != 0:
            return error_results['count'] + 1
        else:
            return 1
        
    def _fetch_prompt(self, prompt_file=None) -> str:
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logging.error(f"{prompt_file} file not found")
            return ""
        except Exception as e:
            logging.error(f"Error reading {prompt_file}: {e}")
            return ""

    def _clean_citations(self, text: str) -> str:
        text = re.sub(r'(\[\d+\])+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
        
    def _clean_markdown(self, text: str) -> str:
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
        
    def _extract_first_paragraph(self, text: str) -> Optional[str]:
        cleaned = self._clean_citations(text)
        cleaned = self._clean_markdown(cleaned)
        cleaned = cleaned.replace('"', '')
        paragraphs = re.split(r'\n\s*\n|^#+\s+', cleaned, flags=re.MULTILINE)
        for para in paragraphs:
            para = para.strip()
            if len(para) >= 50 and re.match(r'^[A-ZÀ-ÿ]', para):
                return para
        return None

    def _extract_last_number(self, text: str) -> Optional[str]:
        cleaned = self._clean_citations(text)
        bold_pattern = r'\*\*(\d+(?:[.,]\d+)?)\*\*'
        bold_matches = re.findall(bold_pattern, text)
        if bold_matches:
            return bold_matches[-1]
        pattern = r'\d+(?:[.,]\d+)?\s*€?'
        matches = re.findall(pattern, text)
        if matches:
            return matches[-1].strip()
        return None

    def _extract_last_url(self, text: str) -> Optional[str]:
        cleaned = self._clean_citations(text)
        pattern = r'https?://[^\s*\)\]\}]+'
        matches = re.findall(pattern, cleaned)
        if matches:
            return matches[-1]
        return None
    
    def _extract_last_json(self, text) -> Optional[Dict]:
        if not isinstance(text, str):
            text = json.dumps(text)
        # First, try to extract JSON from code blocks
        code_block_pattern = r'```(?:json)?\s*(\{[^`]*\})\s*```'
        code_matches = re.findall(code_block_pattern, text, re.DOTALL)
        if code_matches:
            for json_str in reversed(code_matches):
                parsed = self._parse_and_clean_json(json_str)
                if parsed is not None:
                    return parsed
        # Extract all potential JSON objects using brace matching
        json_objects = self._extract_json_objects(text)
        # Try to parse from last to first
        for json_str in reversed(json_objects):
            parsed = self._parse_and_clean_json(json_str)
            if parsed is not None:
                return parsed
        return None


    def _extract_json_objects(self, text: str) -> list:
        json_objects = []
        brace_count = 0
        start_pos = -1
        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_pos = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_pos != -1:
                    json_str = text[start_pos:i+1]
                    json_objects.append(json_str)
                    start_pos = -1
        return json_objects


    def _parse_and_clean_json(self, json_str: str) -> Optional[Dict]:
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            cleaned_str = self._clean_json_string(json_str)
            try:
                parsed = json.loads(cleaned_str)
            except json.JSONDecodeError:
                return None
        cleaned = self._remove_key_value_fields(parsed)
        return cleaned


    def _clean_json_string(self, json_str: str) -> str:
        patterns = [
            (r"'key'\s*:\s*", ""),           # 'key':
            (r'"key"\s*:\s*', ""),           # "key":
            (r"'value'\s*:\s*", ""),         # 'value':
            (r'"value"\s*:\s*', ""),         # "value":
            (r"\bkey\s*:\s*", ""),           # key: (unquoted)
            (r"\bvalue\s*:\s*", ""),         # value: (unquoted)
        ]
        cleaned = json_str
        for pattern, replacement in patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        return cleaned


    def _remove_key_value_fields(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            if set(obj.keys()) == {"key", "value"} and len(obj) == 2:
                return self._remove_key_value_fields(obj["value"])
            cleaned = {}
            for k, v in obj.items():
                if k.lower() not in ['key', 'value']:
                    cleaned[k] = self._remove_key_value_fields(v)
            return cleaned
        elif isinstance(obj, list):
            cleaned_list = []
            for item in obj:
                if isinstance(item, dict) and set(item.keys()) == {"key", "value"}:
                    cleaned_list.append(self._remove_key_value_fields(item["value"]))
                else:
                    cleaned_list.append(self._remove_key_value_fields(item))
            return cleaned_list
        else:
            return obj

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        try:
            result = None
            # ============ Entities ============
            if tool_name == "create_entities":
                result = self.M_client.create_entities(tool_input["entities"])
            elif tool_name == "delete_entities":
                result = self.M_client.delete_entities(tool_input["entity_names"])
            # ============ Relations ============
            elif tool_name == "create_relations":
                result = self.M_client.create_relations(tool_input["relations"])
            elif tool_name == "delete_relations":
                result = self.M_client.delete_relations(tool_input["relations"])
            # ============ Observations ============
            elif tool_name == "add_observations":
                result = self.M_client.add_observations(tool_input["observations"])
            elif tool_name == "delete_observations":
                result = self.M_client.delete_observations(tool_input["deletions"])
            # ============ Graph ============
            elif tool_name == "read_graph":
                result = self.M_client.read_graph()
            # ============ Nodes ============
            elif tool_name == "search_nodes":
                result = self.M_client.search_nodes(tool_input["query"])
            elif tool_name == "open_nodes":
                result = self.M_client.open_nodes(tool_input["names"])
            # ============ Utility ============
            elif tool_name == "status":
                result = self.M_client.status()
            elif tool_name == "reset":
                result = self.M_client.reset()
            elif tool_name == "health":
                result = self.M_client.health()
            else:
                return f"Error: Unknown tool '{tool_name}'"
            # Return result as JSON string
            return json.dumps(result)
        except KeyError as e:
            return f"Error: Missing required parameter {e}"
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"
