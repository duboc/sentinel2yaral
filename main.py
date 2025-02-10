# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import yaml
import streamlit as st
from typing import Union, List, Any
import logging
import vertexai
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmCategory,
    Part,
)
import vertexai.generative_models as generative_models
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

from config.llm_config import llm_config
from config.safety_config import SAFETY_SETTINGS
from config.region_config import AVAILABLE_REGIONS
from config.ui_config import SIDEBAR_CONTENT, LLM_CONTROL_CONFIGS

class GeminiRegionClient:
    def __init__(self, project_id: str = None, logger: logging.Logger = None):
        self.project_id = project_id or os.environ.get("GCP_PROJECT")
        if not self.project_id:
            raise ValueError("Project ID must be provided or set in GCP_PROJECT environment variable")
            
        self.logger = logger or logging.getLogger(__name__)
        self.regions = AVAILABLE_REGIONS
        self.safety_settings = SAFETY_SETTINGS
        
        self.default_generation_config = GenerationConfig(
            max_output_tokens=llm_config.default_max_tokens,
            temperature=llm_config.default_temperature,
            top_p=llm_config.default_top_p,
        )
        
        self.available_models = llm_config.available_models
        self.model_name = self.available_models[0]  # Default to first model

    def _initialize_region(self, region: str) -> None:
        vertexai.init(project=self.project_id, location=region)
        
    def _get_model(self) -> GenerativeModel:
        return GenerativeModel(self.model_name)

    def set_model(self, model_name: str) -> None:
        if model_name not in self.available_models:
            raise ValueError(f"Model {model_name} not available. Choose from {self.available_models}")
        self.model_name = model_name
        
    def update_generation_config(self, temperature: float, max_output_tokens: int, top_p: float) -> None:
        self.default_generation_config = GenerationConfig(
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            top_p=top_p,
        )

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def generate_content(self, prompt: Union[str, List[Union[str, Part]]], **kwargs) -> str:
        last_error = None
        
        for region in self.regions:
            try:
                self._initialize_region(region)
                model = self._get_model()
                
                gen_config = kwargs.pop('generation_config', self.default_generation_config)
                
                response = model.generate_content(
                    prompt,
                    generation_config=gen_config,
                    safety_settings=self.safety_settings,
                    **kwargs
                )
                
                return response.text
                
            except Exception as e:
                self.logger.warning(f"Error with region {region}: {str(e)}")
                last_error = e
        
        raise Exception(f"All regions failed. Last error: {str(last_error)}") from last_error

def load_yaral_examples():
    """Load example YARAL rules from the examples directory."""
    examples = {}
    examples_dir = "examples"
    for filename in os.listdir(examples_dir):
        if filename.endswith(".yaral") and filename.startswith("rule"):
            try:
                with open(os.path.join(examples_dir, filename), 'r') as f:
                    examples[filename] = f.read()
            except Exception as e:
                st.error(f"Error loading {filename}: {str(e)}")
                continue
    return examples

def load_example_rules():
    rules = {}
    examples_dir = "examples"
    for filename in os.listdir(examples_dir):
        if filename.endswith(".yaml"):
            try:
                with open(os.path.join(examples_dir, filename), 'r') as f:
                    rules[filename] = yaml.safe_load(f)
            except yaml.YAMLError as e:
                st.error(f"Error loading {filename}: {str(e)}")
                continue
    return rules

def save_yaral_rule(yaral_content: str, filename: str) -> bool:
    """Save the YARAL rule to a file in the examples directory."""
    try:
        output_filename = os.path.splitext(filename)[0] + '.yaral'
        output_path = os.path.join('examples', output_filename)
        with open(output_path, 'w') as f:
            f.write(yaral_content)
        return True
    except Exception as e:
        st.error(f"Error saving YARAL rule: {str(e)}")
        return False

def convert_to_yaral(client: GeminiRegionClient, rule_content: dict) -> str:
    # Load example YARAL rules
    yaral_examples = load_yaral_examples()
    
    # Create a prompt that includes examples
    examples_text = "\n\n".join([
        f"Example {i+1}:\n```\n{example}\n```"
        for i, example in enumerate(list(yaral_examples.values())[:3])  # Use up to 3 examples
    ])
    
    prompt = f"""Convert this Microsoft Sentinel detection rule to a Chronicle YARAL rule. 
    Here are some examples of well-formatted YARAL rules:
    
    {examples_text}
    
    Here's the Sentinel rule in YAML format that needs to be converted:
    
    {yaml.dump(rule_content, default_flow_style=False)}
    
    Please convert this to a Chronicle YARAL rule format. Focus on:
    1. Maintaining the same detection logic
    2. Using appropriate Chronicle data sources and fields
    3. Preserving the rule's intent and functionality
    4. Following the same structure as the example YARAL rules above
    - rule block with curly braces
    - meta section with description, author, rule_id, and severity
    - events section with event types and variable assignments
    - match section for conditions
    - outcome section for risk scores and output variables
    - condition section at the end"""
    
    try:
        return client.generate_content(prompt)
    except Exception as e:
        st.error(f"Error converting rule: {str(e)}")
        return None

def setup_sidebar():
    """Configure the sidebar with app explanation and LLM settings."""
    st.sidebar.title("About")
    st.sidebar.markdown(SIDEBAR_CONTENT)
    
    st.sidebar.title("LLM Configuration")
    
    # Model selection
    model_name = st.sidebar.selectbox(
        "Select Model",
        llm_config.available_models,
        help="Choose the Gemini model to use for conversion"
    )
    
    # Create sliders using configuration
    controls = {}
    for name, config in LLM_CONTROL_CONFIGS.items():
        controls[name] = st.sidebar.slider(
            name.replace('_', ' ').title(),
            min_value=config["min_value"],
            max_value=config["max_value"],
            value=config["default_value"],
            step=config["step"],
            help=config["help"]
        )
    
    return {
        "model_name": model_name,
        **controls
    }

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    st.set_page_config(page_title="Sentinel to YARAL Converter", layout="wide")
    
    # Setup sidebar and get LLM configuration
    llm_config = setup_sidebar()
    
    st.title("Sentinel to YARAL Rule Converter")
    
    # Initialize GeminiRegionClient
    project_id = os.getenv("GCP_PROJECT")
    if not project_id:
        project_id = st.text_input("Enter your Google Cloud Project ID:")
        if not project_id:
            st.warning("Please create a .env file with GCP_PROJECT or enter your Google Cloud Project ID to continue")
            return
        os.environ["GCP_PROJECT"] = project_id
    
    client = GeminiRegionClient()
    
    # Configure the model based on sidebar settings
    client.set_model(llm_config["model_name"])
    client.update_generation_config(
        temperature=llm_config["temperature"],
        max_output_tokens=llm_config["max_tokens"],
        top_p=llm_config["top_p"]
    )
    
    # Load example rules
    example_rules = load_example_rules()
    
    # Create two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Input")
        input_method = st.radio("Choose input method:", ["Use Example", "Upload YAML"])
        
        if input_method == "Use Example":
            selected_example = st.selectbox("Select an example rule:", list(example_rules.keys()))
            rule_content = example_rules[selected_example]
            st.code(yaml.dump(rule_content, default_flow_style=False), language="yaml")
        else:
            uploaded_file = st.file_uploader("Upload a Sentinel rule YAML file", type="yaml")
            if uploaded_file:
                try:
                    rule_content = yaml.safe_load(uploaded_file)
                    st.code(yaml.dump(rule_content, default_flow_style=False), language="yaml")
                except yaml.YAMLError as e:
                    st.error(f"Error loading YAML file: {str(e)}")
                    rule_content = None
                except Exception as e:
                    st.error(f"Unexpected error: {str(e)}")
                    rule_content = None
            else:
                rule_content = None
        
        if st.button("Convert to YARAL"):
            if rule_content:
                with st.spinner("Converting rule..."):
                    yaral_rule = convert_to_yaral(client, rule_content)
                    if yaral_rule:
                        st.session_state.yaral_rule = yaral_rule
                        if input_method == "Use Example":
                            # Save the YARAL rule alongside the example
                            save_yaral_rule(yaral_rule, selected_example)
    
    with col2:
        st.header("Output")
        if "yaral_rule" in st.session_state and st.session_state.yaral_rule:
            st.code(st.session_state.yaral_rule, language="python")
            
            # Add download button
            st.download_button(
                label="Download YARAL Rule",
                data=st.session_state.yaral_rule,
                file_name="converted_rule.yaral",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
