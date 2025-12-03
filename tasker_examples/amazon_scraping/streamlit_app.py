import streamlit as st
import asyncio
import os
import traceback
from datetime import datetime
from oagi import AsyncScreenshotMaker
from oagi.agent.observer import AsyncAgentObserver
from oagi.agent.tasker import TaskerAgent
from oagi.handler import AsyncPyautoguiActionHandler

# Set page configuration
st.set_page_config(page_title="Amazon Scraping Tasker", page_icon="🛒", layout="wide")

def main():
    st.title("🛒 Amazon Scraping Tasker")

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
        exp_name = st.text_input("Experiment Name", value="amazon_crawl")

    # Main area for Task Definition
    st.header("Task Definition")
    
    col1, col2 = st.columns(2)
    
    with col1:
        product_name = st.text_input("Product Name", value="purse")
    
    default_instruction = "Find the information about the top-selling {product_name} on Amazon"
    instruction_template = st.text_area("Instruction Template", value=default_instruction, height=100)
    
    default_todos = [
        "Open a new tab, go to www.amazon.com, and search for {product_name} in the search bar",
        "Click on 'Sort by' in the top right of the page and select 'Best Sellers'",
    ]
    todos_input = st.text_area("Todos (one per line)", value="\n".join(default_todos), height=150)

    # Construct the final instruction and todos based on inputs
    final_instruction = instruction_template.format(product_name=product_name)
    final_todos = [todo.format(product_name=product_name) for todo in todos_input.split('\n') if todo.strip()]

    st.info(f"**Final Instruction:** {final_instruction}")
    
    if st.button("Run Agent", type="primary", disabled=not api_key):
        run_agent(
            api_key=api_key,
            model_name=model_name,
            max_steps=max_steps,
            temperature=temperature,
            save_dir=save_dir,
            exp_name=exp_name,
            product_name=product_name,
            instruction=final_instruction,
            todos=final_todos
        )

def run_agent(api_key, model_name, max_steps, temperature, save_dir, exp_name, product_name, instruction, todos):
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
            
            try:
                success = await tasker.execute(
                    instruction="",
                    action_handler=action_handler,
                    image_provider=image_provider,
                )
                
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
                output_file = os.path.join(full_save_dir, f"{product_name}_execution_history.html")
                observer.export("html", output_file)
                st.success(f"Execution history exported to: `{output_file}`")
                
                # Provide download link (reading the file we just wrote)
                try:
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label="Download Execution History (HTML)",
                            data=f,
                            file_name=f"{product_name}_execution_history.html",
                            mime="text/html"
                        )
                except Exception as e:
                    st.error(f"Could not prepare download: {e}")

            except Exception as e:
                st.error(f"Error during execution: {e}")
                st.code(traceback.format_exc())

        # Run the async function
        asyncio.run(execute_task())

if __name__ == "__main__":
    main()
