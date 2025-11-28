# OAGI Lux Samples

This repository demonstrates how to leverage **Lux** in various use cases. Lux is a Computer Use foundation model from OpenAGI that enables you to build AI agents capable of automating desktop and web tasks through visual understanding and action execution.

## What is Lux?

Lux provides a `TaskerAgent` that can:
- Execute multi-step workflows defined as "todos"
- Take screenshots and understand UI elements visually
- Perform actions like clicking, typing, and scrolling via PyAutoGUI
- Track execution history and export detailed reports

## Getting Started

1. Install the `oagi` package:
    ```bash
    pip install -r tasker_examples/requirements.txt
    ```
2. Set your API key:
    ```bash
    export OAGI_API_KEY="your-api-key"
    ```

## Examples

All examples are located in the `tasker_examples/` directory.

### Amazon Scraping

**Location:** `tasker_examples/amazon_scraping/`

Searches Amazon for a product and sorts results by best sellers.

```bash
python tasker_examples/amazon_scraping/amazon_scraping.py --product_name "headphones"
```

**Options:**
- `--product_name` - Product to search for (default: `purse`)
- `--exp_name` - Experiment name for saving results (default: `amazon_crawl`)
- `--save_dir` - Directory to save results (default: `results/`)
- `--model_name` - Model to use (default: `lux-actor-1`)
- `--max_steps` - Max steps per todo (default: `24`)

---

### CVS Appointment Booking

**Location:** `tasker_examples/cvs_appointment_booking/`

Navigates CVS.com to schedule a flu shot appointment by filling out forms and selecting options.

```bash
python tasker_examples/cvs_appointment_booking/cvs_tasker.py \
    --first_name "John" \
    --last_name "Doe" \
    --email "john@example.com" \
    --birthday "01-15-1990" \
    --zip_code "10001"
```

**Options:**
- `--first_name` - First name (default: `First`)
- `--last_name` - Last name (default: `Last`)
- `--email` - Email address (default: `user@example.com`)
- `--birthday` - Birthday in MM-DD-YYYY format (default: `MM-DD-YYYY`)
- `--zip_code` - ZIP code for location search (default: `00000`)
- `--exp_name` - Experiment name (default: `cvs`)
- `--save_dir` - Directory to save results (default: `results`)

---

### Software QA with Nuclear Player

**Location:** `tasker_examples/software_qa_with_nuclear/`

Automates UI testing of the Nuclear Player app by clicking through all sidebar buttons and verifying each page loads correctly.

```bash
python tasker_examples/software_qa_with_nuclear/software_qa.py
```

**Options:**
- `--exp_name` - Experiment name (default: `nuclear_qa`)
- `--save_dir` - Directory to save results (default: `results/`)
- `--model_name` - Model to use (default: `lux-actor-1`)
- `--max_steps` - Max steps per todo (default: `24`)

> **Note:** This example requires the [Nuclear Player](https://nuclear.js.org/) app to be installed and running.

---

## Key Components

- **`TaskerAgent`** - The core agent that executes todo-based workflows
- **`AsyncScreenshotMaker`** - Captures screenshots for visual analysis
- **`AsyncPyautoguiActionHandler`** - Executes mouse/keyboard actions
- **`AsyncAgentObserver`** - Records execution history for debugging