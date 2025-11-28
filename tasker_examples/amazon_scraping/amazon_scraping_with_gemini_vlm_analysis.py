import os
import json
import argparse
import base64
import asyncio
import traceback
from datetime import datetime

from oagi import AsyncScreenshotMaker
from oagi.agent.observer import AsyncAgentObserver
from oagi.agent.tasker import TaskerAgent
from oagi.handler import AsyncPyautoguiActionHandler

# Our custom VLM
from model_engine import ModelEngine, ModelInfo


def analyze_screenshot(screenshot_path: str, question: str, vlm: ModelEngine):
    """Encode a screenshot and ask the model to answer `question` about it."""
    if not os.path.exists(screenshot_path):
        raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

    with open(screenshot_path, "rb") as f:
        b64_image = base64.b64encode(f.read()).decode("ascii")

    lower_path = screenshot_path.lower()
    if lower_path.endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    else:
        mime = "image/png"

    user_messages = [
        {"type": "text", "content": question},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_image}"}},
    ]

    # No special system prompt needed; keep it empty to let the model focus on the question.
    return vlm([], user_messages)


async def main():
    parser = argparse.ArgumentParser(description='Crawl Amazon for product data')
    parser.add_argument('--product_name', type=str, default='purse', help='Product name to search for')
    parser.add_argument('--exp_name', type=str, default='amazon_crawl', help='Experiment name')
    parser.add_argument('--model_info_path', type=str, default='apis/gemini.json', help='Path to model info JSON')
    parser.add_argument('--save_dir', type=str, default='results/', help='Directory to save results')
    parser.add_argument('--model_name', type=str, default='lux-actor-1', help='Model name')
    parser.add_argument('--max_steps', type=int, default=24, help='Max steps per todo')
    parser.add_argument('--temperature', type=float, default=0.0, help='Temperature')

    args = parser.parse_args()

    # save directory
    save_dir = os.path.join(args.save_dir, args.exp_name)
    os.makedirs(save_dir, exist_ok=True)

    # load VLM
    with open(args.model_info_path, 'r', encoding='utf-8') as f:
        model_info = json.load(f)
    model_info = ModelInfo(**model_info)
    vlm = ModelEngine(model_info)

    # Define the workflow
    instruction = f"Find the information about the top-selling {args.product_name} on Amazon"
    todos = [
        f"Open a new tab, go to www.amazon.com, and search for {args.product_name} in the search bar",
        f"Click on 'Sort by' in the top right of the page and select 'Best Sellers'",
    ]

    # Initialize automation toolkit
    observer = AsyncAgentObserver()
    image_provider = AsyncScreenshotMaker()
    action_handler = AsyncPyautoguiActionHandler()

    tasker = TaskerAgent(
        api_key=os.getenv("OAGI_API_KEY"),
        base_url=os.getenv("OAGI_BASE_URL", "https://api.agiopen.org"),
        model=args.model_name,
        max_steps=args.max_steps,
        temperature=args.temperature,
        step_observer=observer,
    )

    tasker.set_task(task=instruction, todos=todos)

    print(f"Starting task execution at {datetime.now()}")
    print(f"Task: {instruction}")
    print(f"Number of todos: {len(todos)}")
    print("=" * 60)

    try:
        # Execute the task
        success = await tasker.execute(
            instruction="",
            action_handler=action_handler,
            image_provider=image_provider,
        )

        # Get final memory state
        memory = tasker.get_memory()

        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Overall success: {success}")
        print(f"\nTask execution summary:\n{memory.task_execution_summary}")

        # Print todo statuses
        print("\nTodo Status:")
        for i, todo in enumerate(memory.todos):
            status_icon = {
                "completed": "✅",
                "pending": "⏳",
                "in_progress": "🔄",
                "skipped": "⏭️",
            }.get(todo.status.value, "❓")
            print(f"  {status_icon} [{i + 1}] {todo.description} - {todo.status.value}")

        # Print execution statistics
        status_summary = memory.get_todo_status_summary()
        print("\nExecution Statistics:")
        print(f"  Completed: {status_summary.get('completed', 0)}")
        print(f"  Pending: {status_summary.get('pending', 0)}")
        print(f"  In Progress: {status_summary.get('in_progress', 0)}")
        print(f"  Skipped: {status_summary.get('skipped', 0)}")

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        traceback.print_exc()

    # Analyze the final screenshot with VLM
    screenshot_path = os.path.join(save_dir, f"{args.product_name}_screenshot.png")
    last_screenshot = await image_provider()
    last_screenshot.image.save(screenshot_path)
    
    result = analyze_screenshot(
        screenshot_path,
        "Describe the name, color, price, and discount of the items in the first row of the search results",
        vlm,
    )
    print(f"VLM result: {result}")

    # Save JSON results
    result_path = os.path.join(save_dir, f"{args.product_name}_result.json")
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump({
            "result": result,
            "screenshot_path": screenshot_path,
        }, f, ensure_ascii=False, indent=4)
    print(f"Results saved to {result_path}")

    # Export HTML execution history
    output_file = os.path.join(save_dir, f"{args.product_name}_execution_history.html")
    observer.export("html", output_file)
    print(f"\n📄 Execution history exported to: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())