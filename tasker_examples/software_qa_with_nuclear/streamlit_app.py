import streamlit as st
import asyncio
import os
import traceback
from datetime import datetime
from oagi import AsyncScreenshotMaker
from oagi.agent.observer import AsyncAgentObserver
from oagi.agent.tasker import TaskerAgent
from oagi.handler import AsyncPyautoguiActionHandler
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Set page configuration
st.set_page_config(page_title="Software QA Agent", page_icon="🧪", layout="wide")

def main():
    st.title("🧪 Software QA Agent (Nuclear Player)")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API Key handling
        if "OAGI_API_KEY" in st.secrets:
            api_key = st.secrets["OAGI_API_KEY"]
        else:
            api_key = os.getenv("OAGI_API_KEY", "")
            
        if not api_key:
            st.error("Missing OAGI_API_KEY. Please set it in .streamlit/secrets.toml or environment variables.")
        
        model_name = st.text_input("Model Name", value="lux-actor-1")
        max_steps = st.number_input("Max Steps", min_value=1, value=24)
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.0, step=0.1)
        
        st.subheader("Output Settings")
        save_dir = st.text_input("Save Directory", value="results/")
        exp_name = st.text_input("Experiment Name", value="nuclear_qa")

    # Main area for Task Definition
    st.header("Task Definition")
    
    default_instruction = "QA: click through every sidebar button in the Nuclear Player UI"
    instruction = st.text_area("Instruction", value=default_instruction, height=100)
    
    default_todos = [
        "Click on 'Dashboard' in the left sidebar",
        "Click on 'Downloads' in the left sidebar",
        "Click on 'Lyrics' in the left sidebar",
        "Click on 'Plugins' in the left sidebar",
        "Click on 'Search Results' in the left sidebar",
        "Click on 'Settings' in the left sidebar",
        "Click on 'Equalizer' in the left sidebar",
        "Click on 'Visualizer' in the left sidebar",
        "Click on 'Listening History' in the left sidebar",
        "Click on 'Favorite Albums' in the left sidebar",
        "Click on 'Favorite Tracks' in the left sidebar",
        "Click on 'Favorite Artists' in the left sidebar",
        "Click on 'Local Library' in the left sidebar",
        "Click on 'Playlists' in the left sidebar",
    ]
    todos_input = st.text_area("Todos (one per line)", value="\n".join(default_todos), height=300)

    # Construct the final todos list
    final_todos = [todo.strip() for todo in todos_input.split('\n') if todo.strip()]

    if st.button("Run QA Agent", type="primary", disabled=not api_key):
        run_agent(
            api_key=api_key,
            model_name=model_name,
            max_steps=max_steps,
            temperature=temperature,
            save_dir=save_dir,
            exp_name=exp_name,
            instruction=instruction,
            todos=final_todos
        )

def run_agent(api_key, model_name, max_steps, temperature, save_dir, exp_name, instruction, todos):
    # Setup directories
    full_save_dir = os.path.join(save_dir, exp_name)
    os.makedirs(full_save_dir, exist_ok=True)
    
    # Status container
    status_container = st.container()
    
    with status_container:
        st.write("---")
        st.subheader("Execution Status")
        progress_log = st.empty()
        
        async def execute_task():
            # Initialize components
            observer = AsyncAgentObserver()
            image_provider = AsyncScreenshotMaker()
            action_handler = AsyncPyautoguiActionHandler()
            
            tasker = TaskerAgent(
                api_key=api_key,
                base_url=os.getenv("OAGI_BASE_URL", "https://api.agiopen.org"),
                model=model_name,
                max_steps=max_steps,
                temperature=temperature,
                step_observer=observer,
            )
            
            tasker.set_task(task=instruction, todos=todos)
            
            progress_log.text(f"Starting task execution at {datetime.now()}...\nTask: {instruction}\nNumber of todos: {len(todos)}")
            
            # Define retry strategy
            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type(Exception),
                reraise=True
            )
            async def execute_with_retry():
                return await tasker.execute(
                    instruction="",
                    action_handler=action_handler,
                    image_provider=image_provider,
                )

            try:
                success = await execute_with_retry()
                
                memory = tasker.get_memory()
                
                st.success(f"Execution Completed! Overall success: {success}")
                
                # Display Summary
                st.subheader("Execution Summary")
                st.text(memory.task_execution_summary)
                
                # Display Todo Status
                st.subheader("Todo Status")
                for i, todo in enumerate(memory.todos):
                    status_icon = {
                        "completed": "✅",
                        "pending": "⏳",
                        "in_progress": "🔄",
                        "skipped": "⏭️",
                    }.get(todo.status.value, "❓")
                    st.write(f"{status_icon} **[{i + 1}]** {todo.description} - `{todo.status.value}`")
                
                # Export History
                output_file = os.path.join(full_save_dir, "nuclear_qa_execution_history.html")
                observer.export("html", output_file)
                st.success(f"Execution history exported to: `{output_file}`")
                
                # Provide download link
                try:
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label="Download Execution History (HTML)",
                            data=f,
                            file_name="nuclear_qa_execution_history.html",
                            mime="text/html"
                        )
                except Exception as e:
                    st.error(f"Could not prepare download: {e}")

            except Exception as e:
                st.error(f"Error during execution: {e}")
                if "502" in str(e):
                    st.warning("A 502 Bad Gateway error occurred. This indicates a temporary issue with the API server. The agent attempted to retry but failed. Please try again later.")
                st.code(traceback.format_exc())

        # Run the async function
        asyncio.run(execute_task())

if __name__ == "__main__":
    main()
