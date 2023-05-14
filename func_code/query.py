"""
Class with code related to queries on the dataset
"""
import os, json
import pandas as pd
from tqdm.notebook import tqdm

class Query:
    def __init__(self):
        # self.folderpath_dataset = r"mimic-iv-clinical-database-demo-1.0\mimic-iv-clinical-database-demo-1.0"
        self.folderpath_dataset = r"mimic-iv-clinical-database-demo-2.2\mimic-iv-clinical-database-demo-2.2"
        self.filepath_dataset_metadata = r"dataset_metadata.json"
        with open(self.filepath_dataset_metadata, "r") as f:
            self.dict_metadata = json.load(f)
        
    def get_tablenames_with_colname(self, colname="subject_id"):
        dict_results = {}
        for modulename, dict_tables in self.dict_metadata.items():
            for tablename, dict_tables in dict_tables.items():
                for idx in range(len(dict_tables["columns"]["colname"])):
                    # if dict_metadata["columns"]["colname"][idx] == colname:
                    if colname in dict_tables["columns"]["colname"][idx]:
                        if modulename not in dict_results:
                            dict_results[modulename] = []
                        if tablename not in dict_results[modulename]:
                            dict_results[modulename].append(tablename)
                            
        return dict_results
    
    def load_table(self, modulename, tablename):
        filepath = os.path.join(self.folderpath_dataset, modulename, f"{tablename}.csv.gz")
        return pd.read_csv(filepath, low_memory=False)
    
    def load_data_with_colval(self, colname, colval):
        dict_results = {}
        for modulename, list_tablenames in self.get_tablenames_with_colname(colname=colname).items():
            for tablename in list_tablenames:
                df = self.load_table(modulename=modulename, tablename=tablename)
                df = df[df[colname] == colval]
                if modulename not in dict_results:
                    dict_results[modulename] = {}
                dict_results[modulename][tablename] = df
                
        return dict_results
    
    def update_timestamp_dtype(self, df):
        for colname in df.columns:
            if "time" in colname:
                try:
                    # df[colname] = pd.to_datetime(df[colname], format="%Y-%m-%d %H:%M:%S")
                    df[colname] = pd.to_datetime(df[colname], format="mixed", dayfirst=True)
                except Exception as e:
                    print(e)
        return df
    
    def timestamp2str_df_auto(self, df):
        for colname in df.columns:
            if "time" in colname:
                try:
                    df[colname] = df[colname].dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(e)
        return df
    
    def timestamp2str(self, value):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    
    def update_column_dtype(self, df, col_substring, dtype):
        for colname in df.columns:
            if col_substring in colname:
                try:
                    df[colname] = df[colname].astype(dtype, errors="ignore")
                except Exception as e:
                    print(e)
        return df
    
    def lookup_ref_value(self, id_val, modulename="icu", tablename="d_items", id_colname="itemid", ref_colname="label"):
        df = self.load_table(modulename, tablename)
        ref_value = df[df[id_colname] == id_val][ref_colname].iloc[0]
        return ref_value
    
    def set_subject_id(self, subject_id):
        self.subject_id = subject_id
        self.set_patient_results(subject_id)
    
    def get_subject_id(self):
        return self.subject_id
    
    def set_patient_results(self, subject_id):
        self.dict_patient_results = self.load_data_with_colval(colname="subject_id", colval=subject_id)
    
    def check_variables(self):
        if self.subject_id is None:
            raise Exception("Set `subject_id` first")
        if self.dict_patient_results is None:
            raise Exception("Set `dict_patient_results` first")
        return True
    
    def update_dtypes(self):
        self.check_variables()
        
        for modulename, dict_df_table in self.dict_patient_results.items():
            for tablename, df in dict_df_table.items():
                self.dict_patient_results[modulename][tablename] = self.update_timestamp_dtype(df)
                self.dict_patient_results[modulename][tablename] = self.update_column_dtype(df, col_substring="id", dtype="Int64")
                self.dict_patient_results[modulename][tablename] = self.update_column_dtype(df, col_substring="id", dtype="category")
    
    def get_patient_info(self):
        self.check_variables()
        self.update_dtypes()
        dict_patient_info = self.dict_patient_results["hosp"]["patients"].iloc[0].to_dict()
        
        return {
            "gender": dict_patient_info["gender"],
            "anchor_age": dict_patient_info["anchor_age"],
            "anchor_year": dict_patient_info["anchor_year"],
            "anchor_year_group": dict_patient_info["anchor_year_group"],
            "dod": dict_patient_info["dod"]
        }
    
    def get_timestamp(self, dict_item):
        if "admittime" in dict_item:
            return dict_item["admittime"]
        elif "intime" in dict_item:
            return dict_item["intime"]
        elif "starttime" in dict_item:
            return dict_item["starttime"]
        else:
            return pd.NaT
    
    def get_events(self):
        self.check_variables()
        self.update_dtypes()
        
        df_admissions = self.dict_patient_results["hosp"]["admissions"]
        df_admissions = df_admissions.sort_values(by="admittime", ascending=True)
        list_hadm_ids = df_admissions["hadm_id"].tolist()
        list_dict_admissions = df_admissions.to_dict("records")
        
        dict_output = {"hadm_ids": list_hadm_ids, "hadm": {}}
        
        dict_module_table_pairs_events = {
            "hosp": [
                ("transfer", "transfers")
            ],
            "icu": [
                ("procedureevent", "procedureevents")
            ]
        }
        
        for dict_admission in list_dict_admissions:
            hadm_id = dict_admission["hadm_id"]
            list_dict_admissions_updated = [{"event": "admission"} | {key: value for key, value in dict_admission.items() if key not in ["subject_id", "hadm_id"]} for dict_admission in list_dict_admissions if dict_admission["hadm_id"] == hadm_id]
            dict_output["hadm"][hadm_id] = list_dict_admissions_updated
            
        for modulename, list_tablenames in dict_module_table_pairs_events.items():
            for keyname, tablename in list_tablenames:
                df = self.dict_patient_results[modulename][tablename]
                list_dict_rows = df.to_dict("records")
                for dict_row in list_dict_rows:
                    hadm_id = dict_row["hadm_id"]
                    if hadm_id not in list_hadm_ids:
                        dict_output["hadm"][hadm_id] = []
                    dict_event = {"event": keyname} | {
                        key: value for key, value in dict_row.items() if key not in ["subject_id", "hadm_id"]
                    }
                    dict_output["hadm"][hadm_id].append(dict_event)
                    # dict_output["hadm"][hadm_id] += [{"event": keyname} | {key: value for key, value in dict_row.items() if key not in ["subject_id", "hadm_id"]} for dict_row in list_dict_rows if dict_row["hadm_id"] == hadm_id]
                
        # Sort the events per hadm_id by ascending time
        for hadm_id, list_dict_events in dict_output["hadm"].items():
            list_dict_events_sorted = sorted(list_dict_events, key=self.get_timestamp)
            dict_output["hadm"][hadm_id] = list_dict_events_sorted
            # Format dtypes
            for dict_event_idx, dict_event in enumerate(list_dict_events_sorted):
                for key, value in dict_event.items():
                    if isinstance(value, pd.Timestamp):
                        dict_output["hadm"][hadm_id][dict_event_idx][key] = self.timestamp2str(value)
        
        return dict_output
    
    def get_admission_info(self, modulename, tablename, hadm_id):
        self.check_variables()
        self.update_dtypes()
        
        dict_module_table_pairs_about = {
            "hosp": ["drgcodes", 
                "diagnoses_icd",
                "poe", 
                "pharmacy", 
                "hcpcsevents", 
                "labevents", 
                "microbiologyevents", 
                "procedures_icd",
            ],
            "icu": ["chartevents"]
        }
        
        list_module_table_pairs = []
        for module, list_tables in dict_module_table_pairs_about.items():
            for table in list_tables:
                list_module_table_pairs.append((module, table))
        
        if (modulename, tablename) not in list_module_table_pairs:
            raise Exception(f"Incorrect (module, table) selected {modulename, tablename}. Use one of these - {dict_module_table_pairs_about}")
        
        df = self.dict_patient_results[modulename][tablename]
        df = df[df["hadm_id"] == hadm_id]
        if len(df.index) == 0:
            return {}
        list_dict_rows = df.to_dict("records")
        for row_idx, dict_row in enumerate(list_dict_rows):
            for colname, value in dict_row.items():
                if isinstance(value, pd.Timestamp):
                    list_dict_rows[row_idx][colname] = self.timestamp2str(value)
                    
        return list_dict_rows
    
    def get_patient_timeline(self, subject_id):
        dict_patient_results = self.load_data_with_colval(colname="subject_id", colval=subject_id)
        for modulename, dict_df_table in dict_patient_results.items():
            for tablename, df in dict_df_table.items():
                dict_patient_results[modulename][tablename] = self.update_timestamp_dtype(df)
        dict_patient_info = dict_patient_results["hosp"]["patients"].iloc[0].to_dict()
        
        dict_output = {}
        # Basic patient summary information
        dict_output = {
            "gender": dict_patient_info["gender"],
            "anchor_age": dict_patient_info["anchor_age"],
            "anchor_year": dict_patient_info["anchor_year"],
            "anchor_year_group": dict_patient_info["anchor_year_group"],
            "dod": dict_patient_info["dod"]
        }
        # Updating column dtypes
        for modulename, dict_df_table in dict_patient_results.items():
            for tablename, df in dict_df_table.items():
                dict_patient_results[modulename][tablename] = self.update_column_dtype(df, col_substring="id", dtype="Int64")
                dict_patient_results[modulename][tablename] = self.update_column_dtype(df, col_substring="id", dtype="category")
                
        
        """
        Events
        """
        
        # Admissions
        # Sorted by ascending time
        df_admissions = dict_patient_results["hosp"]["admissions"]
        df_admissions = df_admissions.sort_values(by="admittime", ascending=True)
        list_hadm_ids = df_admissions["hadm_id"].tolist()
        list_dict_admissions = df_admissions.to_dict("records")
        dict_output["hadm"] = {}
        for hadm_id_idx, hadm_id in enumerate(list_hadm_ids):
            dict_output["hadm"][hadm_id] = {"events": [], "about": {}}
            dict_output["hadm"][hadm_id]["events"].append({"event": "admission"} | {key: value for key, value in list_dict_admissions[hadm_id_idx].items() if key not in ["subject_id", "hadm_id"]})
        
        dict_module_table_pairs_events = {
            "hosp": [
                ("transfer", "transfers")
            ],
            "icu": [
                ("procedureevent", "procedureevents")
            ]
        }
        for modulename, list_tablenames in tqdm(dict_module_table_pairs_events.items(), desc="Events"):
            for eventname, tablename in list_tablenames: 
                list_dict_rows = dict_patient_results[modulename][tablename].to_dict("records")
                for dict_row in list_dict_rows:
                    hadm_id = dict_row["hadm_id"]
                    if hadm_id not in dict_output["hadm"]:
                        dict_output["hadm"][hadm_id] = {"events": [], "about": {}}
                    dict_event = {"event": eventname} | {key: value for key, value in dict_row.items() if key not in ["subject_id", "hadm_id"]}
                    if "itemid" in dict_event.keys():
                        dict_event["item_label"] = self.lookup_ref_value(dict_event["itemid"])
                    dict_output["hadm"][hadm_id]["events"].append(dict_event)
            
        
        # # Transfers
        # df_transfers = dict_patient_results["hosp"]["transfers"]
        # list_dict_transfers = df_transfers.to_dict("records")
        # for dict_transfer in list_dict_transfers:
        #     hadm_id = dict_transfer["hadm_id"]
        #     if hadm_id not in dict_output["hadm"]:
        #         dict_output["hadm"][hadm_id] = {"events": [], "about": {}}
        #     dict_output["hadm"][hadm_id]["events"].append({"event": "transfer"} | {key: value for key, value in dict_transfer.items() if key not in ["subject_id", "hadm_id"]})
            
        # # Procedure events
        # df_procedurevents = dict_patient_results["icu"]["procedureevents"]
        # list_dict_procedureevents = df_procedurevents.to_dict("records")
        # for dict_procedureevent in list_dict_procedureevents:
        #     hadm_id = dict_procedureevent["hadm_id"]
        #     if hadm_id not in dict_output["hadm"]:
        #         dict_output["hadm"][hadm_id] = {"events": [], "about": {}}
        #     dict_event = {"event": "procedureevent"} | {key: value for key, value in dict_procedureevent.items() if key not in ["subject_id", "hadm_id"]}
        #     dict_event = {"item_label": self.lookup_ref_value(dict_event["itemid"])} | dict_event
        #     dict_output["hadm"][hadm_id]["events"].append(dict_event)
        
        # Sort the events within every hadm_id
        def get_timestamp(dict_item):
            if "admittime" in dict_item:
                return dict_item["admittime"]
            elif "intime" in dict_item:
                return dict_item["intime"]
            elif "starttime" in dict_item:
                return dict_item["starttime"]
            else:
                return pd.NaT
            
        for hadm_id, dict_items in dict_output["hadm"].items():
            list_dict_events = dict_items["events"]
            dict_output["hadm"][hadm_id]["events"] = sorted(list_dict_events, key=get_timestamp)
        
        # Format the output
        for hadm_id, dict_items in dict_output["hadm"].items():
            list_dict_events = dict_items["events"]
            for event_idx, dict_event in enumerate(list_dict_events):
                for colname, value in dict_event.items():
                    if isinstance(value, pd.Timestamp):
                        dict_output["hadm"][hadm_id]["events"][event_idx][colname] = value.strftime("%Y-%m-%d %H:%M:%S")
        
        
        
        """
        About admissions (crashing)
        """
        
        dict_module_table_pairs_about = {
            "hosp": [
                ("drugs","drgcodes"), 
                # ("diagnoses", "diagnoses_icd"), 
                # ("emar", "emar_detail"),
                # ("poe", "poe"),
                # ("pharmacy", "pharmacy"),
                # ("hcpcs", "hcpcsevents"),
                # ("lab", "labevents"),
                # ("microbiology", "microbiologyevents"),
                # ("procedures", "procedures_icd"),
                # ("omr", "omr")
            ],
            "icu": [
                ("chartevents", "chartevents")
            ]
        }
        for hadm_id, dict_items in tqdm(dict_output["hadm"].items(), desc="About"):
            for modulename, list_tablenames in dict_module_table_pairs_about.items():
                for eventname, tablename in list_tablenames:
                    list_dict_rows = dict_patient_results[modulename][tablename].to_dict("records")
                    list_dict_events = []
                    for dict_row in list_dict_rows:
                        if "itemid" in dict_row:
                            dict_row["item_label"] = self.lookup_ref_value(dict_row["itemid"])
                        dict_row = {key: value for key, value in dict_row.items() if key not in ["subject_id", "hadm_id"]}
                        list_dict_rows.append(dict_row)
                        # list_dict_rows.append({key: value for key, value in dict_row.items() if key not in ["subject_id", "hadm_id"]})
                    # print(list_dict_rows)
                    dict_output["hadm"][hadm_id]["about"] = {eventname: None}
                    dict_output["hadm"][hadm_id]["about"][eventname] = list_dict_rows
                    # print(eventname, tablename)
                    
        # print(dict_row)
           
        return dict_output