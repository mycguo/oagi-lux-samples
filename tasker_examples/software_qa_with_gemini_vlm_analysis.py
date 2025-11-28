import os
import json
import argparse
import base64
import asyncio
import traceback
from datetime import datetime
import logging

from oagi import AsyncScreenshotMaker
from oagi.types import SplitEvent
from oagi.agent.observer import AsyncAgentObserver
from oagi.agent.tasker import TaskerAgent
from oagi.handler import AsyncPyautoguiActionHandler

from model_engine import ModelEngine, ModelInfo

logger = logging.getLogger(__name__)


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

    return vlm([], user_messages)


class QATaskerAgent(TaskerAgent):
    def __init__(self, list_of_checkers: list[str], vlm: ModelEngine, save_dir: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_of_checkers = list_of_checkers
        self.vlm = vlm
        self.save_dir = save_dir
        self.qa_result = {}
    
    async def execute(
        self,
        instruction: str,
        action_handler: AsyncPyautoguiActionHandler,
        image_provider: AsyncScreenshotMaker,
    ):
        overall_success = True

        while True:
            todo_info = self._prepare()

            if todo_info is None:
                logger.info("No more todos to execute")
                break

            todo, todo_index = todo_info
            logger.info(f"Executing todo {todo_index}: {todo.description}")

            if self.step_observer:
                await self.step_observer.on_event(
                    SplitEvent(label=f"Start of todo {todo_index + 1}: {todo.description}")
                )

            success = await self._execute_todo(todo_index, action_handler, image_provider)

            if self.step_observer:
                await self.step_observer.on_event(
                    SplitEvent(label=f"End of todo {todo_index + 1}: {todo.description}")
                )

            if not success:
                logger.warning(f"Todo {todo_index} failed")
                overall_success = False
                break

            self._update_task_summary()

            screenshot_path = os.path.join(
                self.save_dir, 
                f"todo_{todo_index}_{self.list_of_checkers[todo_index]}_screenshot.png"
            )
            last_screenshot = await image_provider()
            last_screenshot.image.save(screenshot_path)
            
            result = analyze_screenshot(
                screenshot_path, 
                f"Check if software is displaying the page of {self.list_of_checkers[todo_index]} with a simple yes or no answer", 
                self.vlm
            )
            print(f"VLM result for {self.list_of_checkers[todo_index]}: {result}")
            self.qa_result[self.list_of_checkers[todo_index]] = result

        status_summary = self.memory.get_todo_status_summary()
        logger.info(f"Workflow complete. Status summary: {status_summary}")

        return overall_success, self.qa_result


async def main():
    parser = argparse.ArgumentParser(description='Run QA Agent on Nuclear Player')
    parser.add_argument('--exp_name', type=str, default='nuclear_qa')
    parser.add_argument('--model_info_path', type=str, default='apis/gemini.json')
    parser.add_argument('--save_dir', type=str, default='results/')
    parser.add_argument('--product_name', type=str, default='nuclear_player')
    parser.add_argument('--model_name', type=str, default='lux-actor-1')
    parser.add_argument('--max_steps', type=int, default=24)
    parser.add_argument('--temperature', type=float, default=0.0)

    args = parser.parse_args()

    save_dir = os.path.join(args.save_dir, args.exp_name)
    os.makedirs(save_dir, exist_ok=True)

    with open(args.model_info_path, 'r', encoding='utf-8') as f:
        model_info = json.load(f)
    model_info = ModelInfo(**model_info)
    vlm = ModelEngine(model_info)

    instruction = "QA: click through every sidebar button in the Nuclear Player UI"
    todos = [
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

    list_of_checkers = [
        "Dashboard", "Downloads", "Lyrics", "Plugins",
        "Search Results", "Settings", "Equalizer", "Visualizer",
        "Listening History", "Favorite Albums", "Favorite Tracks",
        "Favorite Artists", "Local Library", "Playlists",
    ]

    observer = AsyncAgentObserver()
    image_provider = AsyncScreenshotMaker()
    action_handler = AsyncPyautoguiActionHandler()

    tasker = QATaskerAgent(
        api_key=os.getenv("OAGI_API_KEY"),
        base_url=os.getenv("OAGI_BASE_URL", "https://api.agiopen.org"),
        model=args.model_name,
        max_steps=args.max_steps,
        temperature=args.temperature,
        step_observer=observer,
        list_of_checkers=list_of_checkers,
        vlm=vlm,
        save_dir=save_dir,
    )

    tasker.set_task(task=instruction, todos=todos)

    print(f"Starting task execution at {datetime.now()}")
    print(f"Task: {instruction}")
    print(f"Number of todos: {len(todos)}")
    print("=" * 60)

    try:
        success, qa_result = await tasker.execute(
            instruction="",
            action_handler=action_handler,
            image_provider=image_provider,
        )

        memory = tasker.get_memory()

        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Overall success: {success}")
        print(f"\nTask execution summary:\n{memory.task_execution_summary}")

        print("\nTodo Status:")
        for i, todo in enumerate(memory.todos):
            status_icon = {
                "completed": "✅",
                "pending": "⏳",
                "in_progress": "🔄",
                "skipped": "⏭️",
            }.get(todo.status.value, "❓")
            print(f"  {status_icon} [{i + 1}] {todo.description} - {todo.status.value}")

        status_summary = memory.get_todo_status_summary()
        print("\nExecution Statistics:")
        print(f"  Completed: {status_summary.get('completed', 0)}")
        print(f"  Pending: {status_summary.get('pending', 0)}")
        print(f"  In Progress: {status_summary.get('in_progress', 0)}")
        print(f"  Skipped: {status_summary.get('skipped', 0)}")

        print("\nQA Validation Results:")
        for checker, result in qa_result.items():
            print(f"  {checker}: {result}")

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        traceback.print_exc()

    screenshot_path = os.path.join(save_dir, f"{args.product_name}_screenshot.png")
    last_screenshot = await image_provider()
    last_screenshot.image.save(screenshot_path)
    result = analyze_screenshot(
        screenshot_path,
        "List the sidebar buttons visible in the Nuclear Player and describe any that look disabled.",
        vlm,
    )
    print(f"VLM result: {result}")

    output_file = os.path.join(save_dir, "nuclear_qa_execution_history.html")
    observer.export("html", output_file)
    print(f"\n📄 Execution history exported to: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())