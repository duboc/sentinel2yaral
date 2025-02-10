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

SIDEBAR_CONTENT = """
## How to Use
1. **Setup**:
   - Enter your GCP Project ID if not set in `.env`
   - Configure LLM settings below

2. **Input Options**:
   - Use Example: Select from pre-loaded examples
   - Upload YAML: Upload your own Sentinel rule

3. **Convert**:
   - Click 'Convert to YARAL' to generate
   - Download the result using the button

## Environment Setup
1. Copy `.env.example` to `.env`
2. Set your `GCP_PROJECT` in `.env`
3. Install requirements: `pip install -r requirements.txt`
"""

LLM_CONTROL_CONFIGS = {
    "temperature": {
        "min_value": 0.0,
        "max_value": 1.0,
        "default_value": 0.2,
        "step": 0.1,
        "help": "Higher values make output more creative, lower values more focused"
    },
    "max_tokens": {
        "min_value": 1000,
        "max_value": 8192,
        "default_value": 8192,
        "step": 1000,
        "help": "Maximum length of generated response"
    },
    "top_p": {
        "min_value": 0.0,
        "max_value": 1.0,
        "default_value": 0.95,
        "step": 0.05,
        "help": "Nucleus sampling threshold"
    }
} 