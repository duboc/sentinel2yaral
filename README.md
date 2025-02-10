# Sentinel to YARAL Converter

A Streamlit application that converts Microsoft Sentinel detection rules to Chronicle YARAL rules using Google's Gemini AI models.

## Features

- Convert Microsoft Sentinel YAML rules to Chronicle YARAL format
- Support for multiple Gemini AI models
- Configurable LLM parameters (temperature, tokens, etc.)
- Region failover support for better reliability
- Example rules included
- User-friendly interface with explanations

## Project Structure

```
├── config/
│   ├── __init__.py
│   ├── llm_config.py      # LLM model configurations
│   ├── region_config.py   # Available GCP regions
│   ├── safety_config.py   # Safety settings for Gemini
│   └── ui_config.py       # UI text and control configurations
├── examples/
│   ├── rule1.yaml         # Example Sentinel rules
│   └── rule1.yaral        # Converted YARAL rules
├── .env.example           # Example environment variables
├── .gitignore            # Git ignore file
├── main.py               # Main application code
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Vertex AI API enabled
- Google Cloud credentials configured

## Configuration Files

### config/llm_config.py
Defines the LLM configuration including:
- Available Gemini models
- Default parameters (temperature, tokens, etc.)
- Model configuration dataclass

### config/region_config.py
Lists available GCP regions for failover support.

### config/safety_config.py
Configures Gemini's safety settings and harm thresholds.

### config/ui_config.py
Contains UI-related configurations:
- Sidebar content and help text
- LLM control parameters (sliders, inputs)

## Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd sentinel-to-yaral
```

2. Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Cloud credentials:
   - Create or use an existing Google Cloud Project
   - Enable the Vertex AI API
   - Set up authentication by either:
     - Running `gcloud auth application-default login`
     - Setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account key file

5. Set up environment variables:
```bash
cp .env.example .env
```
Edit `.env` and add your Google Cloud Project ID:
```
GCP_PROJECT=your-project-id
```

## Running the Application

### Option 1: Local Installation
1. Start the Streamlit app:
```bash
streamlit run main.py
```

2. Open your web browser and navigate to the URL shown in the terminal (usually http://localhost:8501)

### Option 2: Deploy to Cloud Run

1. Make sure your .env file contains your GCP_PROJECT:
```
GCP_PROJECT=your-project-id
```

2. Run the deployment script:
```bash
./deploy.sh
```

The script will:
- Load the GCP_PROJECT from your .env file
- Deploy directly from source code to Cloud Run
- Set up the environment variables automatically

Note: Cloud Run will automatically build the container from the source code using Cloud Build

## Usage

1. Enter your Google Cloud Project ID when prompted (if not set in .env)
2. Configure LLM settings in the sidebar:
   - Select Gemini model
   - Adjust temperature, max tokens, and top_p values
3. Choose your input method:
   - Use Example: Select from pre-loaded example rules
   - Upload YAML: Upload your own Sentinel rule file
4. Click "Convert to YARAL" to generate the Chronicle YARAL rule
5. The converted rule will appear in the output panel
6. Use the download button to save the YARAL rule to a file

## LLM Configuration

The application supports multiple Gemini models:
- gemini-2.0-flash-001
- gemini-1.5-pro-002
- gemini-1.5-flash-002

Adjustable parameters:
- Temperature (0.0 - 1.0): Controls output creativity
- Max Tokens (1000 - 8192): Controls response length
- Top P (0.0 - 1.0): Controls nucleus sampling

## Region Failover

The application automatically tries different GCP regions if the primary region fails:
- us-central1
- europe-west2
- europe-west3
- asia-northeast1
- australia-southeast1
- asia-south1

## Example Rules

The application comes with example Sentinel rules in the `examples` directory:
- sentinel.yaml
- onedrive.yaml

## Notes

- The conversion process uses Vertex AI's Gemini model to interpret and convert the rules
- The application includes automatic region fallback for better availability
- All generated YARAL rules include comments explaining the conversion choices

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

Apache License 2.0

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
