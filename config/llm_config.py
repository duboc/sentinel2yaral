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

from dataclasses import dataclass
from typing import List

@dataclass
class LLMConfig:
    available_models: List[str] = None
    default_temperature: float = 0.2
    default_max_tokens: int = 8192
    default_top_p: float = 0.95
    
    def __post_init__(self):
        if self.available_models is None:
            self.available_models = [
                "gemini-2.0-flash-001",
                "gemini-1.5-pro-002",
                "gemini-1.5-flash-002"
            ]

llm_config = LLMConfig() 