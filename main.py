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
    """Save the YARAL rule to a file in the output directory."""
    try:
        # Create output directory if it doesn't exist
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(filename))[0]
        output_filename = f"{base_name}_converted.yaral"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w') as f:
            f.write(yaral_content)
        return True
    except Exception as e:
        st.error(f"Error saving YARAL rule: {str(e)}")
        return False

def clean_yaral_content(yaral_content: str) -> str:
    """Clean the YARAL content by removing markdown code blocks and unnecessary comments."""
    # Remove markdown code blocks if present
    content = yaral_content.replace('```yaral', '').replace('```', '')
    
    # Remove leading/trailing whitespace
    content = content.strip()
    
    return content

def convert_to_yaral(client: GeminiRegionClient, rule_content: dict) -> str:
    # Load example YARAL rules
    yaral_examples = load_yaral_examples()
    
    # Create a structured prompt with mapping information and guidelines
    mapping_reference = """
    Common Event Type Mappings:
    - SecurityEvent (EventID 4688) → PROCESS_LAUNCH
    - SigninLogs → USER_LOGIN
    - CommonSecurityLog → NETWORK_CONNECTION
    - AuditLogs → AUDIT_EVENT
    - FileCreateEvents → FILE_CREATION
    - OfficeActivity → RESOURCE_ACCESS
    - AzureActivity → CLOUD_ACTIVITY
    """

    # Create examples section using ALL available YARAL examples
    examples_text = "\n\n".join([
        f"Example - {filename}:\n```\n{content}\n```"
        for filename, content in yaral_examples.items()
        if filename.endswith('.yaral')  # Include all .yaral files
    ])
    
    prompt = f"""Task: Convert the provided Microsoft Sentinel detection rule into a Chronicle Yara-L rule format.

Input Rule Details:
Name: {rule_content.get('name', 'Unknown')}
Description: {rule_content.get('description', 'No description provided')}
Severity: {rule_content.get('severity', 'Medium')}
MITRE Tactics: {', '.join(rule_content.get('tactics', []))}
MITRE Techniques: {', '.join(rule_content.get('techniques', []))}

Original Rule Content:
{yaml.dump(rule_content, default_flow_style=False)}

{mapping_reference}

Reference Examples of Well-Formatted YARAL Rules:
{examples_text}

Output Requirements:
1. Maintain detection logic equivalence while adapting to Yara-L syntax
2. Use appropriate Chronicle data sources and fields based on the mapping reference
3. Preserve the rule's metadata (severity, description, tactics)
4. Follow the same structure as the example YARAL rules:
   - rule block with curly braces
   - meta section with description, author, rule_id, and severity
   - events section with event types and variable assignments
   - match section for conditions
   - outcome section for risk scores and output variables
   - condition section at the end
5. Add comments explaining any complex logic translations
6. Include appropriate time windows and error handling

The author of the rule should always be "Gemini"
Please convert this rule to Chronicle YARAL format while maintaining its detection capabilities and following the patterns shown in the example rules."""

    try:
        yaral_content = client.generate_content(prompt)
        # Clean the content before returning
        return clean_yaral_content(yaral_content)
    except Exception as e:
        st.error(f"Error converting rule: {str(e)}")
        return None

def evaluate_yaral_rule(client: GeminiRegionClient, yaral_content: str) -> str:
    """Evaluate a YARAL rule against best practices and production readiness criteria."""
    prompt = f"""Task: Evaluate the provided Chronicle Yara-L rule against best practices and production readiness criteria.

Input YARAL Rule:
```yaral
{yaral_content}
```

Evaluation Criteria:

1. Structure and Documentation (20 points)
- Complete metadata section (author, description, references)
- Clear comments explaining complex logic
- Proper indentation and formatting
- Documentation of potential false positives
- MITRE ATT&CK mapping accuracy

2. Detection Logic (25 points)
- Proper event type usage
- Correct field references
- Efficient event correlation
- Appropriate time windows
- Logical operator usage

3. Performance Optimization (20 points)
- Efficient use of regex patterns
- Proper use of lookup lists
- Optimal time window definitions
- Resource usage consideration
- Query optimization techniques

4. Error Handling & Resilience (15 points)
- Null value handling
- Missing field handling
- Edge case consideration
- Exception handling
- Graceful failure modes

5. Production Readiness (20 points)
- False positive reduction techniques
- Alert context quality
- Action guidance clarity
- Integration with existing tools
- Scalability considerations

Please provide a detailed evaluation following this format:

Rule Evaluation Report

Rule Name: [Extract from rule]

Overall Score: XX/100

Category Breakdown:
- Structure and Documentation: XX/20
- Detection Logic: XX/25
- Performance Optimization: XX/20
- Error Handling & Resilience: XX/15
- Production Readiness: XX/20

Critical Issues:
1. [Issue description]
2. [Issue description]
...

Strengths:
1. [Strength description]
2. [Strength description]
...

Areas for Improvement:
1. [Area description]
   Recommendation: [Specific improvement suggestion]
   Example:
   ```yaral
   // Code example
   ```

Performance Impact Analysis:
- Resource Usage: [Low/Medium/High]
- Scale Considerations: [Description]
- Optimization Opportunities: [List]

False Positive Analysis:
- Potential Scenarios: [List]
- Suggested Mitigations: [List]

Implementation Recommendations:
1. [Priority 1 change]
2. [Priority 2 change]
...

Final Recommendations:
[Summary of key actions needed for production deployment]"""

    try:
        evaluation = client.generate_content(prompt)
        return evaluation
    except Exception as e:
        st.error(f"Error evaluating rule: {str(e)}")
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
    
    # Create tabs
    tab1, tab2 = st.tabs(["Rule Converter", "Example Rules"])
    
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
    yaral_examples = load_yaral_examples()
    
    with tab1:
        st.title("Sentinel to YARAL Rule Converter")
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
                            # Save the YARAL rule to output directory
                            if save_yaral_rule(yaral_rule, 
                                             selected_example if input_method == "Use Example" else "uploaded_rule"):
                                st.success("Rule converted and saved to output directory!")
        
        with col2:
            st.header("Output")
            if "yaral_rule" in st.session_state and st.session_state.yaral_rule:
                # Display the rule with code formatting
                st.code(st.session_state.yaral_rule, language="python")
                
                # Generate filename for download
                download_filename = (f"{os.path.splitext(selected_example)[0]}_converted.yaral" 
                                  if input_method == "Use Example" 
                                  else "converted_rule.yaral")
                
                # Download button with cleaned content
                st.download_button(
                    label="Download YARAL Rule",
                    data=st.session_state.yaral_rule,
                    file_name=download_filename,
                    mime="text/plain"
                )

                # Add evaluation button
                if st.button("Evaluate Rule"):
                    with st.spinner("Evaluating rule..."):
                        evaluation_result = evaluate_yaral_rule(client, st.session_state.yaral_rule)
                        if evaluation_result:
                            st.session_state.evaluation_result = evaluation_result
                            st.success("Rule evaluation completed!")

                # Display evaluation results if available
                if "evaluation_result" in st.session_state:
                    st.markdown("### Rule Evaluation")
                    st.markdown(st.session_state.evaluation_result)
    
    with tab2:
        st.title("Example YARAL Rules")
        # Filter only rule1 to rule5 yaral files
        rule_files = {k: v for k, v in yaral_examples.items() 
                     if k.startswith('rule') and k.endswith('.yaral') 
                     and k[4:-6].isdigit() and 1 <= int(k[4:-6]) <= 5}
        
        selected_rule = st.selectbox(
            "Select an example YARAL rule to view:",
            options=sorted(rule_files.keys()),
            key="example_rule_selector"
        )
        
        if selected_rule:
            st.code(rule_files[selected_rule], language="python")
            
            # Add download button for the example
            st.download_button(
                label=f"Download {selected_rule}",
                data=rule_files[selected_rule],
                file_name=selected_rule,
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
